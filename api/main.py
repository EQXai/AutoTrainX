"""
FastAPI main application - CLI translator and stats reader.

This application serves as a bridge between web interface and CLI,
translating HTTP requests to CLI commands and reading statistics from PostgreSQL.
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn

from .routes import jobs, training, models
from .services.stats_reader import StatsReader

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown tasks.
    """
    # Startup
    logger.info("AutoTrainX API starting up...")
    
    # Test database connection
    try:
        stats_reader = StatsReader()
        # Test connection with a simple query
        await stats_reader.get_job_statistics()
        logger.info("Database connection verified")
    except Exception as e:
        logger.warning(f"Database connection test failed: {e}")
        logger.info("API will continue - stats may be unavailable")
    
    logger.info("AutoTrainX API startup complete")
    
    yield
    
    # Shutdown
    logger.info("AutoTrainX API shutting down...")
    logger.info("AutoTrainX API shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="AutoTrainX API - CLI Bridge",
        description="""
        API that serves as a bridge between web interface and AutoTrainX CLI.
        
        ## Features
        
        * **Training Execution**: Translate web requests to CLI commands
        * **Statistics Reading**: Read-only access to PostgreSQL job statistics
        * **Simple Interface**: Minimal processing, maximum compatibility
        
        ## How it works
        
        1. **Training**: Web forms → API → CLI commands → main.py execution
        2. **Statistics**: PostgreSQL → API → Web display (read-only)
        
        The API does NOT:
        - Create or manage jobs
        - Modify the database
        - Process datasets
        - Execute training directly
        
        Everything is delegated to the CLI for consistency.
        """,
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(
        training.router,
        prefix="/api/v1/training",
        tags=["training"]
    )
    
    app.include_router(
        jobs.router,
        prefix="/api/v1/jobs",
        tags=["statistics"]
    )
    
    app.include_router(
        models.router,
        prefix="/api/v1/models",
        tags=["models"]
    )

    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors()
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.exception("Unhandled exception occurred")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "type": type(exc).__name__
            }
        )

    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check() -> Dict[str, Any]:
        """
        Health check endpoint to verify API status.
        
        Returns:
            Dictionary with health status information
        """
        # Check CLI availability
        from .services.cli_translator import CLITranslator
        cli_status = "unhealthy"
        try:
            cli = CLITranslator()
            if cli.main_script.exists():
                cli_status = "healthy"
        except:
            pass
        
        # Check database connection
        db_status = "unhealthy"
        try:
            stats = StatsReader()
            await stats.get_job_statistics()
            db_status = "healthy"
        except:
            pass
        
        overall_status = "healthy" if cli_status == "healthy" else "degraded"
        
        return {
            "status": overall_status,
            "services": {
                "cli_translator": cli_status,
                "database_reader": db_status
            },
            "version": "2.0.0",
            "mode": "cli_bridge"
        }

    # Root endpoint
    @app.get("/", tags=["root"])
    async def root() -> Dict[str, str]:
        """
        Root endpoint with API information.
        
        Returns:
            Welcome message and API information
        """
        return {
            "message": "AutoTrainX API - CLI Bridge Mode",
            "version": "2.0.0",
            "description": "Web to CLI translator with read-only statistics",
            "docs": "/docs",
            "health": "/health"
        }

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    # This allows running the app directly with python api/main.py
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
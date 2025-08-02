#!/usr/bin/env python3
"""
AutoTrainX API Server

Main entry point for running the AutoTrainX FastAPI backend server.
This script provides command-line options for configuring and starting
the API server with various deployment options.
"""

import argparse
import logging
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn
from api.main import app


def setup_logging(log_level: str = "info", log_file: str = None):
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level (debug, info, warning, error)
        log_file: Optional log file path
    """
    # Create logs directory if it doesn't exist
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure handlers
    handlers = [logging.StreamHandler()]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    else:
        # Default API log file
        api_log_file = logs_dir / "api_log" / "api_server.log"
        handlers.append(logging.FileHandler(api_log_file))
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)


def validate_environment():
    """
    Validate the environment and required dependencies.
    
    Returns:
        bool: True if environment is valid
    """
    try:
        # Check if src directory exists
        src_dir = project_root / "src"
        if not src_dir.exists():
            print(f"Error: Source directory not found at {src_dir}")
            return False
        
        # Check if database directory exists
        db_dir = project_root / "DB"
        if not db_dir.exists():
            print(f"Warning: Database directory not found at {db_dir}. It will be created automatically.")
            db_dir.mkdir(exist_ok=True)
        
        # Check if workspace directory exists
        workspace_dir = project_root / "workspace"
        if not workspace_dir.exists():
            print(f"Warning: Workspace directory not found at {workspace_dir}. It will be created automatically.")
            workspace_dir.mkdir(exist_ok=True)
            (workspace_dir / "input").mkdir(exist_ok=True)
            (workspace_dir / "output").mkdir(exist_ok=True)
            (workspace_dir / "Presets").mkdir(exist_ok=True)
        
        return True
        
    except Exception as e:
        print(f"Error validating environment: {e}")
        return False


def main():
    """Main entry point for the API server."""
    parser = argparse.ArgumentParser(
        prog="api_server",
        description="AutoTrainX API Server - FastAPI backend for machine learning training pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server with default settings
  python api_server.py
  
  # Start server on custom host and port
  python api_server.py --host 0.0.0.0 --port 8080
  
  # Start server in development mode with auto-reload
  python api_server.py --dev
  
  # Start server in production mode
  python api_server.py --prod --workers 4
  
  # Start server with custom log level
  python api_server.py --log-level debug --log-file api.log
  
  # Check server configuration without starting
  python api_server.py --check-config
        """
    )
    
    # Server configuration
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)"
    )
    
    # Development options
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Run in development mode with auto-reload"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code changes"
    )
    
    # Production options
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Run in production mode"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (production mode only)"
    )
    
    # Logging options
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default="info",
        help="Logging level (default: info)"
    )
    
    parser.add_argument(
        "--log-file",
        help="Log file path (default: logs/api_log/api_server.log)"
    )
    
    # SSL options
    parser.add_argument(
        "--ssl-keyfile",
        help="SSL key file path"
    )
    
    parser.add_argument(
        "--ssl-certfile",
        help="SSL certificate file path"
    )
    
    # Utility options
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Check configuration and exit"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="AutoTrainX API Server 1.0.0"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)
    
    # Validate environment
    if not validate_environment():
        sys.exit(1)
    
    # Check configuration and exit if requested
    if args.check_config:
        print("Checking AutoTrainX API Server configuration...")
        print(f"✓ Project root: {project_root}")
        print(f"✓ Host: {args.host}")
        print(f"✓ Port: {args.port}")
        print(f"✓ Log level: {args.log_level}")
        print(f"✓ Development mode: {args.dev or args.reload}")
        print(f"✓ Production mode: {args.prod}")
        if args.prod:
            print(f"✓ Workers: {args.workers}")
        if args.ssl_keyfile and args.ssl_certfile:
            print(f"✓ SSL enabled: keyfile={args.ssl_keyfile}, certfile={args.ssl_certfile}")
        print("\nConfiguration is valid!")
        return
    
    # Configure server parameters
    server_config = {
        "app": "api.main:app",
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
    }
    
    # Development mode settings
    if args.dev or args.reload:
        server_config.update({
            "reload": True,
            "reload_dirs": [str(project_root / "api"), str(project_root / "src")],
            "access_log": True,
        })
        logger.info("Starting server in development mode with auto-reload")
    
    # Production mode settings
    elif args.prod:
        server_config.update({
            "workers": args.workers,
            "access_log": True,
            "use_colors": False,
        })
        logger.info(f"Starting server in production mode with {args.workers} workers")
    
    # SSL configuration
    if args.ssl_keyfile and args.ssl_certfile:
        if not os.path.exists(args.ssl_keyfile):
            logger.error(f"SSL key file not found: {args.ssl_keyfile}")
            sys.exit(1)
        if not os.path.exists(args.ssl_certfile):
            logger.error(f"SSL certificate file not found: {args.ssl_certfile}")
            sys.exit(1)
        
        server_config.update({
            "ssl_keyfile": args.ssl_keyfile,
            "ssl_certfile": args.ssl_certfile,
        })
        logger.info("SSL enabled")
    
    # Print startup information
    print("=" * 60)
    print("AutoTrainX API Server")
    print("=" * 60)
    print(f"Server URL: {'https' if args.ssl_keyfile else 'http'}://{args.host}:{args.port}")
    print(f"API Documentation: {'https' if args.ssl_keyfile else 'http'}://{args.host}:{args.port}/docs")
    print(f"API Schema: {'https' if args.ssl_keyfile else 'http'}://{args.host}:{args.port}/openapi.json")
    print(f"Health Check: {'https' if args.ssl_keyfile else 'http'}://{args.host}:{args.port}/health")
    print("=" * 60)
    
    try:
        # Start the server
        logger.info(f"Starting AutoTrainX API server on {args.host}:{args.port}")
        uvicorn.run(**server_config)
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
        print("\nShutting down AutoTrainX API server...")
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        print(f"Error: Failed to start server - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
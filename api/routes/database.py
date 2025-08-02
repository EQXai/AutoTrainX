"""
Database management API routes.

This module provides REST endpoints for database exploration and management,
including viewing tables, schemas, and data.
"""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Path as PathParam, status
from fastapi.responses import JSONResponse
import sqlite3

from ..models.schemas import BaseResponse
from ..dependencies import get_pipeline_service
from ..exceptions import AutoTrainXAPIException

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db_connection(pipeline):
    """Get database connection from pipeline service."""
    # Check multiple possible database locations
    possible_paths = [
        Path(pipeline.base_path) / "DB" / "executions.db",  # Primary location
        Path(pipeline.base_path) / "autotrainx.db",        # Alternative location
        Path(pipeline.base_path) / "database.db",          # Another alternative
    ]
    
    db_path = None
    for path in possible_paths:
        if path.exists():
            db_path = path
            logger.info(f"Found database at: {db_path}")
            break
    
    if not db_path:
        # If no database found, use the primary location
        db_path = possible_paths[0]
        if not db_path.exists():
            raise AutoTrainXAPIException(
                message=f"Database file not found. Checked locations: {[str(p) for p in possible_paths]}",
                error_code="DATABASE_NOT_FOUND"
            )
    
    return sqlite3.connect(str(db_path))


@router.get(
    "/tables",
    response_model=dict,
    summary="List database tables",
    description="""
    Retrieve a list of all tables in the database with their basic information.
    
    Returns:
    - Table names
    - Row counts
    - Column information
    """
)
async def list_tables(
    pipeline = Depends(get_pipeline_service)
) -> dict:
    """List all tables in the database."""
    logger.info("Listing database tables")
    
    try:
        conn = get_db_connection(pipeline)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = cursor.fetchall()
        
        table_info = []
        for (table_name,) in tables:
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Get column information
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = []
            for col in cursor.fetchall():
                columns.append({
                    "name": col[1],
                    "type": col[2],
                    "nullable": not col[3],
                    "primary_key": bool(col[5])
                })
            
            table_info.append({
                "name": table_name,
                "row_count": row_count,
                "columns": columns
            })
        
        conn.close()
        
        return {
            "tables": table_info,
            "total_tables": len(table_info)
        }
        
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to list tables: {str(e)}",
            error_code="DATABASE_LIST_ERROR"
        )


@router.get(
    "/tables/{table_name}/data",
    response_model=dict,
    summary="Get table data",
    description="""
    Retrieve data from a specific table with pagination support.
    
    Parameters:
    - table_name: Name of the table
    - limit: Maximum number of rows to return (default: 100, max: 1000)
    - offset: Number of rows to skip (default: 0)
    """
)
async def get_table_data(
    table_name: str = PathParam(..., description="Table name"),
    limit: int = Query(100, ge=1, le=1000, description="Number of rows to return"),
    offset: int = Query(0, ge=0, description="Number of rows to skip"),
    pipeline = Depends(get_pipeline_service)
) -> dict:
    """Get data from a specific table."""
    logger.info(f"Getting data from table: {table_name}")
    
    try:
        conn = get_db_connection(pipeline)
        cursor = conn.cursor()
        
        # Validate table name (prevent SQL injection)
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=? AND name NOT LIKE 'sqlite_%'
        """, (table_name,))
        if not cursor.fetchone():
            raise AutoTrainXAPIException(
                message=f"Table not found: {table_name}",
                error_code="TABLE_NOT_FOUND"
            )
        
        # Get total row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_count = cursor.fetchone()[0]
        
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Get data with pagination
        cursor.execute(f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", (limit, offset))
        rows = cursor.fetchall()
        
        conn.close()
        
        return {
            "table_name": table_name,
            "columns": columns,
            "rows": rows,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except AutoTrainXAPIException:
        raise
    except Exception as e:
        logger.error(f"Error getting table data: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to get table data: {str(e)}",
            error_code="DATABASE_DATA_ERROR"
        )


@router.get(
    "/tables/{table_name}/schema",
    response_model=dict,
    summary="Get table schema",
    description="""
    Retrieve detailed schema information for a specific table.
    
    Returns:
    - Column definitions
    - Indexes
    - Foreign keys
    - Constraints
    """
)
async def get_table_schema(
    table_name: str = PathParam(..., description="Table name"),
    pipeline = Depends(get_pipeline_service)
) -> dict:
    """Get detailed schema for a specific table."""
    logger.info(f"Getting schema for table: {table_name}")
    
    try:
        conn = get_db_connection(pipeline)
        cursor = conn.cursor()
        
        # Validate table name
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name=? AND name NOT LIKE 'sqlite_%'
        """, (table_name,))
        result = cursor.fetchone()
        if not result:
            raise AutoTrainXAPIException(
                message=f"Table not found: {table_name}",
                error_code="TABLE_NOT_FOUND"
            )
        
        create_sql = result[0]
        
        # Get column information
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = []
        for col in cursor.fetchall():
            columns.append({
                "cid": col[0],
                "name": col[1],
                "type": col[2],
                "not_null": bool(col[3]),
                "default_value": col[4],
                "primary_key": bool(col[5])
            })
        
        # Get indexes
        cursor.execute(f"PRAGMA index_list({table_name})")
        indexes = []
        for idx in cursor.fetchall():
            cursor.execute(f"PRAGMA index_info({idx[1]})")
            index_columns = [col[2] for col in cursor.fetchall()]
            indexes.append({
                "name": idx[1],
                "unique": bool(idx[2]),
                "columns": index_columns
            })
        
        # Get foreign keys
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        foreign_keys = []
        for fk in cursor.fetchall():
            foreign_keys.append({
                "id": fk[0],
                "table": fk[2],
                "from": fk[3],
                "to": fk[4],
                "on_update": fk[5],
                "on_delete": fk[6]
            })
        
        conn.close()
        
        return {
            "table_name": table_name,
            "create_sql": create_sql,
            "columns": columns,
            "indexes": indexes,
            "foreign_keys": foreign_keys
        }
        
    except AutoTrainXAPIException:
        raise
    except Exception as e:
        logger.error(f"Error getting table schema: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to get table schema: {str(e)}",
            error_code="DATABASE_SCHEMA_ERROR"
        )


@router.post(
    "/query",
    response_model=dict,
    summary="Execute custom query",
    description="""
    Execute a custom SQL query on the database.
    
    **WARNING**: This endpoint allows direct SQL execution. Use with caution.
    Only SELECT queries are allowed by default.
    """
)
async def execute_query(
    query: str,
    pipeline = Depends(get_pipeline_service)
) -> dict:
    """Execute a custom SQL query."""
    logger.info("Executing custom query")
    
    try:
        # Basic security check - only allow SELECT queries
        if not query.strip().upper().startswith("SELECT"):
            raise AutoTrainXAPIException(
                message="Only SELECT queries are allowed",
                error_code="QUERY_NOT_ALLOWED"
            )
        
        conn = get_db_connection(pipeline)
        cursor = conn.cursor()
        
        cursor.execute(query)
        
        # Get column names
        columns = [description[0] for description in cursor.description] if cursor.description else []
        
        # Get results
        rows = cursor.fetchall()
        
        conn.close()
        
        return {
            "query": query,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows)
        }
        
    except AutoTrainXAPIException:
        raise
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to execute query: {str(e)}",
            error_code="QUERY_EXECUTION_ERROR"
        )


@router.get(
    "/stats",
    response_model=dict,
    summary="Get database statistics",
    description="""
    Get overall database statistics including size, table counts, and more.
    """
)
async def get_database_stats(
    pipeline = Depends(get_pipeline_service)
) -> dict:
    """Get database statistics."""
    logger.info("Getting database statistics")
    
    try:
        # Find the actual database path
        possible_paths = [
            Path(pipeline.base_path) / "DB" / "executions.db",
            Path(pipeline.base_path) / "autotrainx.db",
            Path(pipeline.base_path) / "database.db",
        ]
        
        db_path = None
        db_size = 0
        for path in possible_paths:
            if path.exists():
                db_path = path
                db_size = path.stat().st_size
                break
        
        conn = get_db_connection(pipeline)
        cursor = conn.cursor()
        
        # Get table count
        cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        table_count = cursor.fetchone()[0]
        
        # Get total row count across all tables
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        tables = cursor.fetchall()
        
        total_rows = 0
        table_stats = []
        for (table_name,) in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            total_rows += row_count
            table_stats.append({
                "table": table_name,
                "rows": row_count
            })
        
        conn.close()
        
        return {
            "database_size_mb": round(db_size / (1024 * 1024), 2),
            "table_count": table_count,
            "total_rows": total_rows,
            "table_stats": sorted(table_stats, key=lambda x: x["rows"], reverse=True)
        }
        
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to get database stats: {str(e)}",
            error_code="DATABASE_STATS_ERROR"
        )


# Health check endpoint for database router
@router.get(
    "/health",
    response_model=dict,
    tags=["health"],
    summary="Database service health check"
)
async def database_health_check(
    pipeline = Depends(get_pipeline_service)
) -> dict:
    """Check health of database service."""
    try:
        # Try to connect to database
        conn = get_db_connection(pipeline)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
        return {
            "status": "healthy",
            "service": "database",
            "message": "Database service is operational"
        }
        
    except Exception as e:
        logger.error(f"Database service health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "database",
                "error": str(e),
                "message": "Database service is not operational"
            }
        )
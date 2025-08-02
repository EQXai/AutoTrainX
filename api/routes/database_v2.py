"""
Database management API routes (v2 - Multi-database support).

This module provides REST endpoints for database exploration and management,
supporting both SQLite and PostgreSQL databases.
"""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Path as PathParam, status
from fastapi.responses import JSONResponse
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

from ..models.schemas import BaseResponse
from ..dependencies import get_database_manager
from ..exceptions import AutoTrainXAPIException
from src.database.manager_v2 import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/tables", response_model=BaseResponse)
async def list_tables(
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> BaseResponse:
    """
    List all tables in the database.
    
    Returns:
        BaseResponse with list of table names
    """
    try:
        with db_manager.get_session() as session:
            # Get database engine
            engine = session.get_bind()
            
            # Use SQLAlchemy inspector to get tables
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            return BaseResponse(
                success=True,
                message=f"Found {len(tables)} tables",
                data={"tables": tables}
            )
            
    except SQLAlchemyError as e:
        logger.error(f"Database error listing tables: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to list tables: {str(e)}",
            error_code="DATABASE_ERROR"
        )
    except Exception as e:
        logger.error(f"Unexpected error listing tables: {e}")
        raise AutoTrainXAPIException(
            message=f"Unexpected error: {str(e)}",
            error_code="INTERNAL_ERROR"
        )


@router.get("/tables/{table_name}/schema", response_model=BaseResponse)
async def get_table_schema(
    table_name: str = PathParam(..., description="Name of the table"),
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> BaseResponse:
    """
    Get schema information for a specific table.
    
    Args:
        table_name: Name of the table to inspect
        
    Returns:
        BaseResponse with table schema information
    """
    try:
        with db_manager.get_session() as session:
            engine = session.get_bind()
            inspector = inspect(engine)
            
            # Check if table exists
            if table_name not in inspector.get_table_names():
                raise AutoTrainXAPIException(
                    message=f"Table '{table_name}' not found",
                    error_code="TABLE_NOT_FOUND"
                )
            
            # Get columns
            columns = []
            for col in inspector.get_columns(table_name):
                columns.append({
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "default": str(col["default"]) if col["default"] else None,
                    "autoincrement": col.get("autoincrement", False)
                })
            
            # Get primary keys
            pk_constraint = inspector.get_pk_constraint(table_name)
            primary_keys = pk_constraint["constrained_columns"] if pk_constraint else []
            
            # Get foreign keys
            foreign_keys = []
            for fk in inspector.get_foreign_keys(table_name):
                foreign_keys.append({
                    "columns": fk["constrained_columns"],
                    "referred_table": fk["referred_table"],
                    "referred_columns": fk["referred_columns"]
                })
            
            # Get indexes
            indexes = []
            for idx in inspector.get_indexes(table_name):
                indexes.append({
                    "name": idx["name"],
                    "columns": idx["column_names"],
                    "unique": idx["unique"]
                })
            
            return BaseResponse(
                success=True,
                message=f"Schema for table '{table_name}'",
                data={
                    "table_name": table_name,
                    "columns": columns,
                    "primary_keys": primary_keys,
                    "foreign_keys": foreign_keys,
                    "indexes": indexes
                }
            )
            
    except AutoTrainXAPIException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error getting schema: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to get table schema: {str(e)}",
            error_code="DATABASE_ERROR"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting schema: {e}")
        raise AutoTrainXAPIException(
            message=f"Unexpected error: {str(e)}",
            error_code="INTERNAL_ERROR"
        )


@router.get("/tables/{table_name}/data", response_model=BaseResponse)
async def get_table_data(
    table_name: str = PathParam(..., description="Name of the table"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of rows to return"),
    offset: Optional[int] = Query(0, ge=0, description="Number of rows to skip"),
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> BaseResponse:
    """
    Get data from a specific table with pagination.
    
    Args:
        table_name: Name of the table to query
        limit: Maximum number of rows to return
        offset: Number of rows to skip
        
    Returns:
        BaseResponse with table data and row count
    """
    try:
        with db_manager.get_session() as session:
            engine = session.get_bind()
            inspector = inspect(engine)
            
            # Check if table exists
            if table_name not in inspector.get_table_names():
                raise AutoTrainXAPIException(
                    message=f"Table '{table_name}' not found",
                    error_code="TABLE_NOT_FOUND"
                )
            
            # Validate table name to prevent SQL injection
            if not table_name.isidentifier():
                raise AutoTrainXAPIException(
                    message=f"Invalid table name: '{table_name}'",
                    error_code="INVALID_TABLE_NAME"
                )
            
            # Get total row count
            count_query = text(f"SELECT COUNT(*) FROM {table_name}")
            total_rows = session.execute(count_query).scalar()
            
            # Get column names
            columns = [col["name"] for col in inspector.get_columns(table_name)]
            
            # Get data with pagination
            data_query = text(f"SELECT * FROM {table_name} LIMIT :limit OFFSET :offset")
            result = session.execute(data_query, {"limit": limit, "offset": offset})
            
            # Convert rows to dictionaries
            rows = []
            for row in result:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Convert non-serializable types to strings
                    if isinstance(value, (bytes, bytearray)):
                        value = value.hex()
                    elif value is not None and not isinstance(value, (str, int, float, bool, list, dict)):
                        value = str(value)
                    row_dict[col] = value
                rows.append(row_dict)
            
            return BaseResponse(
                success=True,
                message=f"Retrieved {len(rows)} rows from '{table_name}'",
                data={
                    "table_name": table_name,
                    "columns": columns,
                    "rows": rows,
                    "total_rows": total_rows,
                    "limit": limit,
                    "offset": offset
                }
            )
            
    except AutoTrainXAPIException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error getting data: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to get table data: {str(e)}",
            error_code="DATABASE_ERROR"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting data: {e}")
        raise AutoTrainXAPIException(
            message=f"Unexpected error: {str(e)}",
            error_code="INTERNAL_ERROR"
        )


@router.post("/query", response_model=BaseResponse)
async def execute_query(
    query_request: Dict[str, Any],
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> BaseResponse:
    """
    Execute a read-only SQL query.
    
    Args:
        query_request: Dictionary containing 'query' field with SQL statement
        
    Returns:
        BaseResponse with query results
    """
    try:
        query = query_request.get("query", "").strip()
        
        if not query:
            raise AutoTrainXAPIException(
                message="Query cannot be empty",
                error_code="INVALID_QUERY"
            )
        
        # Only allow SELECT queries for safety
        if not query.upper().startswith("SELECT"):
            raise AutoTrainXAPIException(
                message="Only SELECT queries are allowed",
                error_code="FORBIDDEN_QUERY"
            )
        
        # Basic SQL injection prevention
        forbidden_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE"]
        query_upper = query.upper()
        for keyword in forbidden_keywords:
            if keyword in query_upper:
                raise AutoTrainXAPIException(
                    message=f"Query contains forbidden keyword: {keyword}",
                    error_code="FORBIDDEN_QUERY"
                )
        
        with db_manager.get_session() as session:
            # Execute query
            result = session.execute(text(query))
            
            # Get column names
            columns = list(result.keys()) if result.returns_rows else []
            
            # Get rows
            rows = []
            if result.returns_rows:
                for row in result:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        # Convert non-serializable types
                        if isinstance(value, (bytes, bytearray)):
                            value = value.hex()
                        elif value is not None and not isinstance(value, (str, int, float, bool, list, dict)):
                            value = str(value)
                        row_dict[col] = value
                    rows.append(row_dict)
            
            return BaseResponse(
                success=True,
                message=f"Query executed successfully",
                data={
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows)
                }
            )
            
    except AutoTrainXAPIException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error executing query: {e}")
        raise AutoTrainXAPIException(
            message=f"Query execution failed: {str(e)}",
            error_code="QUERY_ERROR"
        )
    except Exception as e:
        logger.error(f"Unexpected error executing query: {e}")
        raise AutoTrainXAPIException(
            message=f"Unexpected error: {str(e)}",
            error_code="INTERNAL_ERROR"
        )


@router.get("/info", response_model=BaseResponse)
async def get_database_info(
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> BaseResponse:
    """
    Get general database information.
    
    Returns:
        BaseResponse with database type and connection info
    """
    try:
        with db_manager.get_session() as session:
            engine = session.get_bind()
            
            # Get database type
            dialect_name = engine.dialect.name
            
            # Get database URL (sanitized)
            db_url = str(engine.url)
            # Hide password in URL
            if "@" in db_url and ":" in db_url.split("@")[0]:
                parts = db_url.split("@")
                user_pass = parts[0].split("//")[1]
                user = user_pass.split(":")[0]
                sanitized_url = f"{db_url.split('//')[0]}//{user}:***@{parts[1]}"
            else:
                sanitized_url = db_url
            
            # Get table count
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            # For PostgreSQL, get additional info
            db_info = {
                "dialect": dialect_name,
                "url": sanitized_url,
                "table_count": len(tables),
                "tables": tables
            }
            
            if dialect_name == "postgresql":
                # Get database size
                try:
                    size_query = text("SELECT pg_database_size(current_database())")
                    db_size = session.execute(size_query).scalar()
                    db_info["size_bytes"] = db_size
                    db_info["size_human"] = f"{db_size / 1024 / 1024:.2f} MB"
                except:
                    pass
            
            return BaseResponse(
                success=True,
                message="Database information retrieved",
                data=db_info
            )
            
    except SQLAlchemyError as e:
        logger.error(f"Database error getting info: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to get database info: {str(e)}",
            error_code="DATABASE_ERROR"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting info: {e}")
        raise AutoTrainXAPIException(
            message=f"Unexpected error: {str(e)}",
            error_code="INTERNAL_ERROR"
        )
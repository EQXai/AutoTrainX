"""
Dataset path management endpoints.
"""

import os
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from ..dependencies import get_pipeline_service
from ..models.schemas import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter()


class DatasetPath(BaseModel):
    """Dataset path model."""
    id: int
    path: str
    added_at: str
    dataset_count: int = 0


class AddPathRequest(BaseModel):
    """Request to add a dataset path."""
    path: str


class DatasetInfo(BaseModel):
    """Information about a discovered dataset."""
    name: str
    path: str
    image_count: int
    caption_count: int
    has_valid_structure: bool
    parent_path: str


def get_db_path(pipeline) -> Path:
    """Get the database path for dataset paths."""
    base_path = Path(pipeline.base_path)
    db_dir = base_path / "DB"
    db_dir.mkdir(exist_ok=True)
    return db_dir / "dataset_paths.db"


def init_db(db_path: Path):
    """Initialize the dataset paths database."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dataset_paths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            added_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()


def is_valid_dataset(path: Path) -> tuple[bool, int, int]:
    """
    Check if a directory contains a valid dataset structure.
    Returns (is_valid, image_count, caption_count)
    """
    if not path.is_dir():
        return False, 0, 0
    
    # Count images and captions
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    images = []
    captions = []
    
    for file in path.iterdir():
        if file.is_file():
            if file.suffix.lower() in image_extensions:
                images.append(file)
            elif file.suffix.lower() == '.txt':
                captions.append(file)
    
    # A valid dataset should have at least one image
    is_valid = len(images) > 0
    
    return is_valid, len(images), len(captions)


def scan_directory_for_datasets(path: Path, max_depth: int = 3) -> List[DatasetInfo]:
    """
    Recursively scan a directory for datasets.
    """
    datasets = []
    
    def scan_recursive(current_path: Path, depth: int = 0):
        if depth > max_depth:
            return
        
        try:
            for item in current_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # Check if this directory is a dataset
                    is_valid, image_count, caption_count = is_valid_dataset(item)
                    
                    if is_valid:
                        datasets.append(DatasetInfo(
                            name=item.name,
                            path=str(item),
                            image_count=image_count,
                            caption_count=caption_count,
                            has_valid_structure=True,
                            parent_path=str(path)
                        ))
                    else:
                        # If not a dataset, scan subdirectories
                        scan_recursive(item, depth + 1)
        except PermissionError:
            logger.warning(f"Permission denied accessing: {current_path}")
        except Exception as e:
            logger.error(f"Error scanning {current_path}: {e}")
    
    scan_recursive(path)
    return datasets


@router.get(
    "/paths",
    response_model=List[DatasetPath],
    summary="List dataset paths",
    description="Get all configured dataset search paths"
)
async def list_dataset_paths(
    pipeline = Depends(get_pipeline_service)
) -> List[DatasetPath]:
    """List all dataset paths."""
    db_path = get_db_path(pipeline)
    init_db(db_path)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, path, added_at FROM dataset_paths ORDER BY added_at DESC")
    rows = cursor.fetchall()
    
    paths = []
    for row in rows:
        path = Path(row[1])
        dataset_count = 0
        
        if path.exists():
            # Count datasets in this path
            datasets = scan_directory_for_datasets(path)
            dataset_count = len(datasets)
        
        paths.append(DatasetPath(
            id=row[0],
            path=row[1],
            added_at=row[2],
            dataset_count=dataset_count
        ))
    
    conn.close()
    return paths


@router.post(
    "/paths",
    response_model=DatasetPath,
    status_code=status.HTTP_201_CREATED,
    summary="Add dataset path",
    description="Add a new path to scan for datasets"
)
async def add_dataset_path(
    request: AddPathRequest,
    pipeline = Depends(get_pipeline_service)
) -> DatasetPath:
    """Add a new dataset path."""
    path = Path(request.path)
    
    # Validate path exists and is a directory
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path does not exist: {request.path}"
        )
    
    if not path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path is not a directory: {request.path}"
        )
    
    db_path = get_db_path(pipeline)
    init_db(db_path)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        added_at = datetime.utcnow().isoformat()
        cursor.execute(
            "INSERT INTO dataset_paths (path, added_at) VALUES (?, ?)",
            (str(path), added_at)
        )
        conn.commit()
        
        # Get the inserted row
        cursor.execute("SELECT id FROM dataset_paths WHERE path = ?", (str(path),))
        row_id = cursor.fetchone()[0]
        
        # Count datasets
        datasets = scan_directory_for_datasets(path)
        
        return DatasetPath(
            id=row_id,
            path=str(path),
            added_at=added_at,
            dataset_count=len(datasets)
        )
        
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Path already exists: {request.path}"
        )
    finally:
        conn.close()


@router.delete(
    "/paths/{path_id}",
    response_model=BaseResponse,
    summary="Remove dataset path",
    description="Remove a dataset search path"
)
async def remove_dataset_path(
    path_id: int,
    pipeline = Depends(get_pipeline_service)
) -> BaseResponse:
    """Remove a dataset path."""
    db_path = get_db_path(pipeline)
    
    if not db_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No dataset paths configured"
        )
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM dataset_paths WHERE id = ?", (path_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path with ID {path_id} not found"
        )
    
    conn.commit()
    conn.close()
    
    return BaseResponse(
        success=True,
        message=f"Path removed successfully"
    )


@router.get(
    "/scan",
    response_model=List[DatasetInfo],
    summary="Scan for datasets",
    description="Scan all configured paths for available datasets"
)
async def scan_datasets(
    pipeline = Depends(get_pipeline_service)
) -> List[DatasetInfo]:
    """Scan all paths for datasets."""
    db_path = get_db_path(pipeline)
    
    if not db_path.exists():
        return []
    
    init_db(db_path)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("SELECT path FROM dataset_paths")
    rows = cursor.fetchall()
    conn.close()
    
    all_datasets = []
    
    # Get workspace path to exclude it from external scans
    workspace_input = Path(pipeline.base_path) / "workspace" / "input"
    workspace_input_str = str(workspace_input.resolve())
    
    # Scan all configured paths
    for row in rows:
        path = Path(row[0])
        if path.exists():
            datasets = scan_directory_for_datasets(path)
            # Filter out datasets that are in the workspace
            for dataset in datasets:
                dataset_path = Path(dataset.path).resolve()
                # Skip if this dataset is inside the workspace
                if not str(dataset_path).startswith(workspace_input_str):
                    all_datasets.append(dataset)
    
    # Remove duplicates based on path
    seen_paths = set()
    unique_datasets = []
    for dataset in all_datasets:
        if dataset.path not in seen_paths:
            seen_paths.add(dataset.path)
            unique_datasets.append(dataset)
    
    return unique_datasets


@router.post(
    "/scan/{path_id}",
    response_model=List[DatasetInfo],
    summary="Scan specific path",
    description="Scan a specific path for datasets"
)
async def scan_path(
    path_id: int,
    pipeline = Depends(get_pipeline_service)
) -> List[DatasetInfo]:
    """Scan a specific path for datasets."""
    db_path = get_db_path(pipeline)
    
    if not db_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No dataset paths configured"
        )
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("SELECT path FROM dataset_paths WHERE id = ?", (path_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path with ID {path_id} not found"
        )
    
    path = Path(row[0])
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path no longer exists: {row[0]}"
        )
    
    return scan_directory_for_datasets(path)
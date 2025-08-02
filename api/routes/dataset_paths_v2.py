"""
Dataset path management endpoints with multi-database support.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

from ..dependencies import get_pipeline_service
from ..models.schemas import BaseResponse
from ...src.database.factory import DatabaseFactory, DatabaseConfig
from ...src.database.config import db_settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Define dataset paths model
Base = declarative_base()


class DatasetPathModel(Base):
    """SQLAlchemy model for dataset paths."""
    __tablename__ = 'dataset_paths'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(Text, unique=True, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)


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


class DatasetPathsDB:
    """Database manager for dataset paths."""
    
    def __init__(self, db_url: Optional[str] = None):
        """Initialize database connection.
        
        Args:
            db_url: Database URL. If None, uses configuration.
        """
        if db_url is None:
            # Use dataset paths specific URL
            db_url = db_settings.get_dataset_paths_url()
        
        # Parse URL to determine database type
        if db_url.startswith('sqlite://'):
            db_path = db_url.replace('sqlite:///', '')
            self.config = DatabaseConfig(
                db_type='sqlite',
                db_path=Path(db_path)
            )
        else:
            self.config = DatabaseConfig(
                db_type='postgresql',
                db_url=db_url
            )
        
        # Create engine
        self.engine = DatabaseFactory.create_engine(self.config)
        
        # Create tables
        Base.metadata.create_all(self.engine)
        
        # Create session factory
        from sqlalchemy.orm import sessionmaker
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()


# Global database instance
_db_instance = None


def get_dataset_paths_db() -> DatasetPathsDB:
    """Get or create database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatasetPathsDB()
    return _db_instance


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
    db = get_dataset_paths_db()
    
    with db.get_session() as session:
        paths_models = session.query(DatasetPathModel).order_by(
            DatasetPathModel.added_at.desc()
        ).all()
        
        paths = []
        for path_model in paths_models:
            path = Path(path_model.path)
            dataset_count = 0
            
            if path.exists():
                # Count datasets in this path
                datasets = scan_directory_for_datasets(path)
                dataset_count = len(datasets)
            
            paths.append(DatasetPath(
                id=path_model.id,
                path=path_model.path,
                added_at=path_model.added_at.isoformat(),
                dataset_count=dataset_count
            ))
    
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
    
    db = get_dataset_paths_db()
    
    with db.get_session() as session:
        try:
            # Create new path entry
            path_model = DatasetPathModel(
                path=str(path),
                added_at=datetime.utcnow()
            )
            session.add(path_model)
            session.commit()
            session.refresh(path_model)
            
            # Count datasets
            datasets = scan_directory_for_datasets(path)
            
            return DatasetPath(
                id=path_model.id,
                path=path_model.path,
                added_at=path_model.added_at.isoformat(),
                dataset_count=len(datasets)
            )
            
        except Exception as e:
            # Check if it's a unique constraint violation
            if "UNIQUE constraint failed" in str(e) or "duplicate key value" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Path already exists: {request.path}"
                )
            raise


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
    db = get_dataset_paths_db()
    
    with db.get_session() as session:
        path_model = session.query(DatasetPathModel).filter_by(id=path_id).first()
        
        if not path_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Path with ID {path_id} not found"
            )
        
        session.delete(path_model)
        session.commit()
    
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
    db = get_dataset_paths_db()
    
    with db.get_session() as session:
        path_models = session.query(DatasetPathModel).all()
    
    all_datasets = []
    
    # Get workspace path to exclude it from external scans
    workspace_input = Path(pipeline.base_path) / "workspace" / "input"
    workspace_input_str = str(workspace_input.resolve())
    
    # Scan all configured paths
    for path_model in path_models:
        path = Path(path_model.path)
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
    db = get_dataset_paths_db()
    
    with db.get_session() as session:
        path_model = session.query(DatasetPathModel).filter_by(id=path_id).first()
    
    if not path_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path with ID {path_id} not found"
        )
    
    path = Path(path_model.path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path no longer exists: {path_model.path}"
        )
    
    return scan_directory_for_datasets(path)
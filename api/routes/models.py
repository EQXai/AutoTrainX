"""
Models routes - Manage model paths and browse trained models.

These routes provide access to model information stored in PostgreSQL.
"""

import logging
import os
import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
import asyncpg
from uuid import uuid4

import os

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models for requests/responses
class ModelPath(BaseModel):
    id: str
    path: str
    added_at: datetime
    last_scan: Optional[datetime]
    model_count: int = 0


class Model(BaseModel):
    id: str
    name: str
    path: str
    type: str
    size: int
    created_at: Optional[datetime]
    modified_at: Optional[datetime]
    has_preview: bool = False
    preview_images: Optional[List[str]] = None
    metadata: Optional[dict] = None


class AddPathRequest(BaseModel):
    path: str


class ModelPathsResponse(BaseModel):
    paths: List[ModelPath]


class ModelsResponse(BaseModel):
    models: List[Model]


class ScanResponse(BaseModel):
    success: bool
    models_found: int
    message: str


async def get_connection():
    """Get database connection."""
    # Get database configuration from environment variables
    return await asyncpg.connect(
        host=os.getenv('AUTOTRAINX_DB_HOST', 'localhost'),
        port=int(os.getenv('AUTOTRAINX_DB_PORT', '5432')),
        user=os.getenv('AUTOTRAINX_DB_USER', 'autotrainx'),
        password=os.getenv('AUTOTRAINX_DB_PASSWORD', os.getenv('DATABASE_PASSWORD', 'AutoTrainX2024Secure123')),
        database=os.getenv('AUTOTRAINX_DB_NAME', 'autotrainx')
    )


@router.get("/paths", response_model=ModelPathsResponse)
async def get_model_paths():
    """Get all registered model paths."""
    conn = None
    try:
        conn = await get_connection()
        
        rows = await conn.fetch("""
            SELECT id, path, added_at, last_scan, model_count
            FROM model_paths
            ORDER BY path
        """)
        
        paths = [
            ModelPath(
                id=row['id'],
                path=row['path'],
                added_at=row['added_at'],
                last_scan=row['last_scan'],
                model_count=row['model_count'] or 0
            )
            for row in rows
        ]
        
        return ModelPathsResponse(paths=paths)
        
    except Exception as e:
        logger.error(f"Failed to get model paths: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve model paths: {str(e)}"
        )
    finally:
        if conn:
            await conn.close()


@router.post("/paths", response_model=ModelPath)
async def add_model_path(request: AddPathRequest):
    """Add a new model path to monitor."""
    conn = None
    try:
        # Validate path exists
        if not os.path.exists(request.path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path does not exist: {request.path}"
            )
        
        if not os.path.isdir(request.path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path is not a directory: {request.path}"
            )
        
        conn = await get_connection()
        
        # Generate ID
        path_id = str(uuid4())[:8]
        
        # Insert path
        try:
            await conn.execute("""
                INSERT INTO model_paths (id, path, added_at, model_count)
                VALUES ($1, $2, $3, 0)
            """, path_id, request.path, datetime.now())
        except asyncpg.UniqueViolationError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Path already exists: {request.path}"
            )
        
        return ModelPath(
            id=path_id,
            path=request.path,
            added_at=datetime.now(),
            last_scan=None,
            model_count=0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add model path: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add model path: {str(e)}"
        )
    finally:
        if conn:
            await conn.close()


@router.delete("/paths/{path_id}")
async def remove_model_path(path_id: str):
    """Remove a model path."""
    conn = None
    try:
        conn = await get_connection()
        
        # Delete associated models first
        await conn.execute("DELETE FROM models WHERE path_id = $1", path_id)
        
        # Delete path
        result = await conn.execute("DELETE FROM model_paths WHERE id = $1", path_id)
        
        if result.split()[-1] == '0':
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Path not found: {path_id}"
            )
        
        return {"success": True, "message": "Path removed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove model path: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove model path: {str(e)}"
        )
    finally:
        if conn:
            await conn.close()


@router.get("", response_model=ModelsResponse)
async def get_models():
    """Get all models from registered paths."""
    conn = None
    try:
        conn = await get_connection()
        
        rows = await conn.fetch("""
            SELECT id, name, path, type, size, created_at, modified_at,
                   has_preview, preview_images, model_metadata
            FROM models
            ORDER BY modified_at DESC
        """)
        
        models = []
        for row in rows:
            # Parse preview_images JSON if it's a string
            preview_images = row['preview_images']
            if preview_images and isinstance(preview_images, str):
                try:
                    preview_images = json.loads(preview_images)
                except:
                    preview_images = None
            
            # Parse metadata JSON if it's a string
            metadata = row['model_metadata']
            if metadata and isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = None
            
            model = Model(
                id=row['id'],
                name=row['name'],
                path=row['path'],
                type=row['type'],
                size=row['size'],
                created_at=row['created_at'],
                modified_at=row['modified_at'],
                has_preview=row['has_preview'] or False,
                preview_images=preview_images,
                metadata=metadata
            )
            models.append(model)
        
        return ModelsResponse(models=models)
        
    except Exception as e:
        logger.error(f"Failed to get models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve models: {str(e)}"
        )
    finally:
        if conn:
            await conn.close()


@router.post("/scan", response_model=ScanResponse)
async def scan_for_models(request: AddPathRequest):
    """Scan a path for models and update the database."""
    conn = None
    try:
        if not os.path.exists(request.path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path does not exist: {request.path}"
            )
        
        conn = await get_connection()
        
        # Get path ID
        path_row = await conn.fetchrow(
            "SELECT id FROM model_paths WHERE path = $1",
            request.path
        )
        
        if not path_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Path not registered: {request.path}"
            )
        
        path_id = path_row['id']
        
        # Scan for model files
        model_extensions = ['.safetensors', '.ckpt', '.pt', '.pth']
        models_found = 0
        
        for root, dirs, files in os.walk(request.path):
            for file in files:
                if any(file.endswith(ext) for ext in model_extensions):
                    file_path = os.path.join(root, file)
                    
                    # Get file info
                    stat = os.stat(file_path)
                    
                    # Generate model ID
                    model_id = str(uuid4())[:8]
                    
                    # Check if model already exists
                    existing = await conn.fetchval(
                        "SELECT id FROM models WHERE path = $1",
                        file_path
                    )
                    
                    if not existing:
                        # Check for preview images
                        model_dir = os.path.dirname(file_path)
                        preview_dir = os.path.join(model_dir, 'Preview')
                        preview_images = []
                        has_preview = False
                        
                        if os.path.exists(preview_dir) and os.path.isdir(preview_dir):
                            # Look for image files in Preview directory
                            image_extensions = ['.png', '.jpg', '.jpeg', '.webp']
                            for preview_file in os.listdir(preview_dir):
                                if any(preview_file.lower().endswith(ext) for ext in image_extensions):
                                    preview_images.append(preview_file)
                            
                            if preview_images:
                                has_preview = True
                        
                        # Insert new model
                        await conn.execute("""
                            INSERT INTO models (id, name, path, type, size, 
                                              created_at, modified_at, path_id,
                                              has_preview, preview_images)
                            VALUES ($1, $2, $3, $4, $5::bigint, $6, $7, $8, $9, $10)
                        """, model_id, file, file_path, 
                            file.split('.')[-1], stat.st_size,
                            datetime.fromtimestamp(stat.st_ctime),
                            datetime.fromtimestamp(stat.st_mtime),
                            path_id, has_preview, 
                            json.dumps(preview_images) if preview_images else None)
                        
                        models_found += 1
                    else:
                        # Update existing model with preview info if needed
                        model_dir = os.path.dirname(file_path)
                        preview_dir = os.path.join(model_dir, 'Preview')
                        preview_images = []
                        has_preview = False
                        
                        if os.path.exists(preview_dir) and os.path.isdir(preview_dir):
                            image_extensions = ['.png', '.jpg', '.jpeg', '.webp']
                            for preview_file in os.listdir(preview_dir):
                                if any(preview_file.lower().endswith(ext) for ext in image_extensions):
                                    preview_images.append(preview_file)
                            
                            if preview_images:
                                has_preview = True
                        
                        await conn.execute("""
                            UPDATE models 
                            SET has_preview = $1, preview_images = $2
                            WHERE path = $3
                        """, has_preview, 
                            json.dumps(preview_images) if preview_images else None,
                            file_path)
        
        # Update path scan info with total count
        total_count = await conn.fetchval(
            "SELECT COUNT(*) FROM models WHERE path_id = $1",
            path_id
        )
        
        await conn.execute("""
            UPDATE model_paths 
            SET last_scan = $1, model_count = $2
            WHERE id = $3
        """, datetime.now(), total_count, path_id)
        
        return ScanResponse(
            success=True,
            models_found=models_found,
            message=f"Found {models_found} new models"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to scan for models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scan for models: {str(e)}"
        )
    finally:
        if conn:
            await conn.close()


@router.get("/{model_id}/preview/{image_name}")
async def get_model_preview(model_id: str, image_name: str):
    """Get a preview image for a model."""
    conn = None
    try:
        conn = await get_connection()
        
        # Get model info
        model = await conn.fetchrow(
            "SELECT path, preview_images FROM models WHERE id = $1",
            model_id
        )
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model not found: {model_id}"
            )
        
        # Check if image is in preview list
        preview_images = model['preview_images'] or []
        if isinstance(preview_images, str):
            try:
                preview_images = json.loads(preview_images)
            except:
                preview_images = []
        
        if image_name not in preview_images:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Preview image not found: {image_name}"
            )
        
        # Build image path
        model_dir = os.path.dirname(model['path'])
        image_path = os.path.join(model_dir, 'Preview', image_name)
        
        if not os.path.exists(image_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image file not found: {image_path}"
            )
        
        # Return the image file
        return FileResponse(
            image_path,
            media_type=f"image/{image_name.split('.')[-1].lower()}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get preview image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve preview image: {str(e)}"
        )
    finally:
        if conn:
            await conn.close()


@router.get("/health")
async def health_check():
    """Check if models service is healthy."""
    try:
        conn = await get_connection()
        await conn.fetchval("SELECT 1")
        await conn.close()
        
        return {
            "status": "healthy",
            "message": "Models service is working"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
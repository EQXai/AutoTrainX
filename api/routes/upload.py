"""
File upload endpoints for datasets.
"""

import os
import shutil
from pathlib import Path
from typing import List
import logging

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from fastapi.responses import JSONResponse

from ..dependencies import get_pipeline_service
from ..models.schemas import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/dataset",
    response_model=BaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload dataset files",
    description="""
    Upload multiple files for a dataset.
    
    Files are saved to workspace/input/{dataset_name}/
    Supports images (jpg, jpeg, png, webp) and text files (txt).
    """
)
async def upload_dataset_files(
    dataset_name: str = Form(..., description="Name of the dataset"),
    files: List[UploadFile] = File(..., description="Files to upload"),
    pipeline = Depends(get_pipeline_service)
) -> BaseResponse:
    """Upload dataset files."""
    
    logger.info(f"Received upload request for dataset: {dataset_name} with {len(files)} files")
    
    try:
        # Validate dataset name
        if not dataset_name or "/" in dataset_name or "\\" in dataset_name or " " in dataset_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid dataset name. Use only letters, numbers, hyphens and underscores."
            )
        
        # Create target directory
        base_path = Path(pipeline.base_path)
        target_dir = base_path / "workspace" / "input" / dataset_name
        
        # Check if dataset already exists
        if target_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Dataset '{dataset_name}' already exists"
            )
        
        # Create directory
        target_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {target_dir}")
        
        uploaded_files = []
        
        for file in files:
            if not file.filename:
                continue
                
            # Validate file type
            file_ext = Path(file.filename).suffix.lower()
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.txt'}
            
            if file_ext not in allowed_extensions:
                # Clean up and raise error
                shutil.rmtree(target_dir)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File type '{file_ext}' not allowed. Allowed types: {', '.join(allowed_extensions)}"
                )
            
            # Save file
            file_path = target_dir / file.filename
            
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            uploaded_files.append(file.filename)
            logger.info(f"Uploaded file: {file_path}")
        
        # Validate that we have both images and captions
        image_files = [f for f in uploaded_files if Path(f).suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}]
        text_files = [f for f in uploaded_files if Path(f).suffix.lower() == '.txt']
        
        logger.info(f"Successfully uploaded {len(uploaded_files)} files to {target_dir}")
        
        return BaseResponse(
            success=True,
            message=f"Successfully uploaded {len(uploaded_files)} files",
            data={
                "dataset_name": dataset_name,
                "path": str(target_dir.relative_to(base_path)),
                "file_count": len(uploaded_files),
                "image_count": len(image_files),
                "caption_count": len(text_files)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        if 'target_dir' in locals() and target_dir.exists():
            try:
                shutil.rmtree(target_dir)
            except:
                pass
        
        logger.error(f"Failed to upload dataset: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload dataset: {str(e)}"
        )


@router.delete(
    "/dataset/{dataset_name}",
    response_model=BaseResponse,
    summary="Delete uploaded dataset",
    description="Delete an uploaded dataset that hasn't been prepared yet"
)
async def delete_uploaded_dataset(
    dataset_name: str,
    pipeline = Depends(get_pipeline_service)
) -> BaseResponse:
    """Delete uploaded dataset files."""
    
    base_path = Path(pipeline.base_path)
    target_dir = base_path / "workspace" / "input" / dataset_name
    
    if not target_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_name}' not found"
        )
    
    try:
        shutil.rmtree(target_dir)
        logger.info(f"Deleted uploaded dataset: {target_dir}")
        
        return BaseResponse(
            success=True,
            message=f"Successfully deleted dataset '{dataset_name}'"
        )
        
    except Exception as e:
        logger.error(f"Failed to delete dataset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete dataset: {str(e)}"
        )
"""
Dataset management API routes.

This module provides REST endpoints for managing training datasets,
including listing, viewing, preparing, and organizing datasets.
"""

import logging
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Path as PathParam, UploadFile, File, status
from fastapi.responses import JSONResponse, FileResponse
from PIL import Image

from ..models.schemas import (
    DatasetInfo, DatasetListResponse, DatasetPreparationRequest, DatasetPreparationResponse,
    BaseResponse, PaginatedResponse
)
from ..dependencies import get_pipeline_service, get_pagination_params, validate_dataset_name
from ..exceptions import (
    DatasetNotFoundError, DatasetPreparationError, AutoTrainXAPIException
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/",
    response_model=DatasetListResponse,
    summary="List available datasets",
    description="""
    Retrieve a paginated list of available datasets.
    
    Returns both prepared datasets (ready for training) and input datasets
    (raw datasets that need preparation).
    
    **Dataset Types:**
    - **Prepared**: Datasets that have been processed and are ready for training
    - **Input**: Raw datasets that need preparation before training
    
    **Information Included:**
    - Dataset name and path
    - Number of images and text files
    - Creation timestamp and size
    - Preparation status
    """
)
async def list_datasets(
    pagination: dict = Depends(get_pagination_params),
    dataset_type: Optional[str] = Query(None, description="Filter by type: 'prepared', 'input', or 'all'"),
    pipeline = Depends(get_pipeline_service)
) -> DatasetListResponse:
    """List available datasets with pagination."""
    logger.info(f"Listing datasets with type filter: {dataset_type}")
    
    try:
        datasets = []
        
        # Only get input datasets - ignore prepared datasets from output folder
        input_path = Path(pipeline.base_path) / "workspace" / "input"
        if input_path.exists():
            for dataset_dir in input_path.iterdir():
                if dataset_dir.is_dir():
                    # Count files
                    image_count = len([f for f in dataset_dir.iterdir() 
                                     if f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}])
                    text_count = len([f for f in dataset_dir.iterdir() 
                                    if f.suffix.lower() == '.txt'])
                    
                    datasets.append(DatasetInfo(
                        name=dataset_dir.name,  # Remove "(input)" suffix since we only show input datasets
                        path=str(dataset_dir),
                        total_images=image_count,
                        total_texts=text_count,
                        has_sample_prompts=False,
                        created_at=None,
                        size_mb=None
                    ))
        
        # Apply pagination
        total_count = len(datasets)
        start_idx = pagination["offset"]
        end_idx = start_idx + pagination["page_size"]
        paginated_datasets = datasets[start_idx:end_idx]
        
        response = DatasetListResponse(
            items=paginated_datasets,
            total_count=total_count,
            page=pagination["page"],
            page_size=pagination["page_size"],
            total_pages=(total_count + pagination["page_size"] - 1) // pagination["page_size"]
        )
        
        logger.info(f"Retrieved {len(paginated_datasets)} datasets (total: {total_count})")
        return response
        
    except Exception as e:
        logger.error(f"Error listing datasets: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to list datasets: {str(e)}",
            error_code="DATASET_LIST_ERROR"
        )


@router.get(
    "/{dataset_name}",
    response_model=DatasetInfo,
    summary="Get dataset details",
    description="""
    Retrieve detailed information about a specific dataset.
    
    Returns comprehensive dataset information including:
    - File counts and organization
    - Sample prompts availability
    - Dataset structure and paths
    - Preparation status
    """
)
async def get_dataset(
    dataset_name: str = PathParam(..., description="Dataset name"),
    pipeline = Depends(get_pipeline_service)
) -> DatasetInfo:
    """Get detailed information about a specific dataset."""
    dataset_name = validate_dataset_name(dataset_name)
    logger.info(f"Retrieving dataset info: {dataset_name}")
    
    try:
        # Only check input dataset - ignore prepared datasets
        input_path = Path(pipeline.base_path) / "workspace" / "input" / dataset_name
        if input_path.exists() and input_path.is_dir():
            # Count files
            image_count = len([f for f in input_path.iterdir() 
                             if f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}])
            text_count = len([f for f in input_path.iterdir() 
                            if f.suffix.lower() == '.txt'])
            
            return DatasetInfo(
                name=dataset_name,  # Remove "(input)" suffix
                path=str(input_path),
                total_images=image_count,
                total_texts=text_count,
                has_sample_prompts=False,
                created_at=None,
                size_mb=None
            )
        
        # Dataset not found
        raise DatasetNotFoundError(dataset_name)
        
    except DatasetNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error retrieving dataset {dataset_name}: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to retrieve dataset: {str(e)}",
            error_code="DATASET_RETRIEVAL_ERROR"
        )


@router.post(
    "/prepare",
    response_model=DatasetPreparationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Prepare dataset for training",
    description="""
    Prepare a raw dataset for training.
    
    This endpoint processes raw image and text files into the format
    required for training, including:
    
    **Preparation Steps:**
    1. Copy and organize files into training structure
    2. Generate repeated training samples based on specified count
    3. Create class-based directory structure
    4. Validate image and text file pairs
    5. Generate sample prompts file
    
    **Parameters:**
    - **source_path**: Path to raw dataset directory
    - **repeats**: Number of times to repeat each sample (default: 30)
    - **class_name**: Class name for training (default: "person")
    - **auto_clean**: Whether to clean up temporary files (default: false)
    
    **Response:**
    Returns immediately with preparation job information.
    The actual preparation runs asynchronously.
    """
)
async def prepare_dataset(
    request: DatasetPreparationRequest,
    pipeline = Depends(get_pipeline_service)
) -> DatasetPreparationResponse:
    """Prepare a dataset for training."""
    logger.info(f"Preparing dataset from: {request.source_path}")
    
    try:
        # Validate source path exists
        source_path = Path(request.source_path)
        if not source_path.exists():
            raise DatasetPreparationError(
                request.source_path,
                "Source path does not exist"
            )
        
        if not source_path.is_dir():
            raise DatasetPreparationError(
                request.source_path,
                "Source path must be a directory"
            )
        
        # Check for image files
        image_files = list(source_path.glob("*.jpg")) + \
                     list(source_path.glob("*.jpeg")) + \
                     list(source_path.glob("*.png")) + \
                     list(source_path.glob("*.webp"))
        
        if not image_files:
            raise DatasetPreparationError(
                request.source_path,
                "No image files found in source directory"
            )
        
        # Prepare dataset using pipeline
        result = pipeline.prepare_dataset_only(
            source_path=request.source_path,
            repeats=request.repeats,
            class_name=request.class_name,
            auto_clean=request.auto_clean
        )
        
        if result.status.name == "SUCCESS":
            # Extract dataset name from result
            dataset_name = source_path.name
            output_path = pipeline.dataset_preparator.output_path / dataset_name
            
            logger.info(f"Successfully prepared dataset: {dataset_name}")
            
            return DatasetPreparationResponse(
                success=True,
                message=f"Dataset '{dataset_name}' prepared successfully",
                dataset_name=dataset_name,
                output_path=str(output_path),
                stats={
                    "total_images": len(image_files),
                    "repeats": request.repeats,
                    "class_name": request.class_name,
                    "successful_datasets": result.successful_datasets,
                    "processing_time": getattr(result, 'processing_time', 0)
                }
            )
        else:
            raise DatasetPreparationError(
                request.source_path,
                result.error_message or "Dataset preparation failed"
            )
            
    except (DatasetPreparationError, DatasetNotFoundError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error preparing dataset: {e}")
        raise DatasetPreparationError(request.source_path, str(e))


@router.delete(
    "/{dataset_name}",
    response_model=BaseResponse,
    summary="Delete a dataset",
    description="""
    Delete a prepared dataset and all associated files.
    
    **Warning:** This action cannot be undone. All training data,
    configurations, and results associated with this dataset will be removed.
    
    **Requirements:**
    - Dataset must not be currently in use by any running training job
    - User must have appropriate permissions
    """
)
async def delete_dataset(
    dataset_name: str = PathParam(..., description="Dataset name"),
    pipeline = Depends(get_pipeline_service)
) -> BaseResponse:
    """Delete a prepared dataset."""
    dataset_name = validate_dataset_name(dataset_name)
    logger.info(f"Deleting dataset: {dataset_name}")
    
    try:
        # Check if dataset exists
        dataset_info = pipeline.get_dataset_info(dataset_name)
        if not dataset_info:
            raise DatasetNotFoundError(dataset_name)
        
        # Delete dataset directory
        import shutil
        dataset_path = Path(dataset_info["dataset_dir"])
        if dataset_path.exists():
            shutil.rmtree(dataset_path)
            logger.info(f"Deleted dataset directory: {dataset_path}")
        
        # TODO: Check for active training jobs using this dataset
        # TODO: Clean up associated configurations and results
        
        return BaseResponse(
            success=True,
            message=f"Dataset '{dataset_name}' deleted successfully"
        )
        
    except DatasetNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error deleting dataset {dataset_name}: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to delete dataset: {str(e)}",
            error_code="DATASET_DELETION_ERROR"
        )


@router.get(
    "/{dataset_name}/files",
    response_model=dict,
    summary="List dataset files",
    description="""
    List files within a specific dataset.
    
    Returns information about all files in the dataset including:
    - Image files and their properties
    - Text caption files
    - Generated configuration files
    - Sample prompts and other metadata
    """
)
async def list_dataset_files(
    dataset_name: str = PathParam(..., description="Dataset name"),
    file_type: Optional[str] = Query(None, description="Filter by file type: 'images', 'texts', 'configs', 'all'"),
    pipeline = Depends(get_pipeline_service)
) -> dict:
    """List files within a dataset."""
    dataset_name = validate_dataset_name(dataset_name)
    logger.info(f"Listing files for dataset: {dataset_name}")
    
    try:
        # Get dataset info
        dataset_info = pipeline.get_dataset_info(dataset_name)
        if not dataset_info:
            raise DatasetNotFoundError(dataset_name)
        
        dataset_path = Path(dataset_info["dataset_dir"])
        files_info = {
            "dataset_name": dataset_name,
            "dataset_path": str(dataset_path),
            "files": {
                "images": [],
                "texts": [],
                "configs": [],
                "other": []
            }
        }
        
        # Scan training directory
        training_dir = dataset_path / "img"
        if training_dir.exists():
            for subdir in training_dir.iterdir():
                if subdir.is_dir():
                    for file_path in subdir.iterdir():
                        if file_path.is_file():
                            file_info = {
                                "name": file_path.name,
                                "path": str(file_path),
                                "size": file_path.stat().st_size,
                                "modified": file_path.stat().st_mtime
                            }
                            
                            if file_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}:
                                files_info["files"]["images"].append(file_info)
                            elif file_path.suffix.lower() == '.txt':
                                files_info["files"]["texts"].append(file_info)
                            else:
                                files_info["files"]["other"].append(file_info)
        
        # Scan for config files
        if dataset_path.exists():
            for file_path in dataset_path.rglob("*.toml"):
                file_info = {
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": file_path.stat().st_size,
                    "modified": file_path.stat().st_mtime
                }
                files_info["files"]["configs"].append(file_info)
        
        # Filter by file type if specified
        if file_type and file_type != "all":
            if file_type in files_info["files"]:
                files_info["files"] = {file_type: files_info["files"][file_type]}
            else:
                files_info["files"] = {}
        
        # Add summary
        files_info["summary"] = {
            "total_images": len(files_info["files"].get("images", [])),
            "total_texts": len(files_info["files"].get("texts", [])),
            "total_configs": len(files_info["files"].get("configs", [])),
            "total_other": len(files_info["files"].get("other", []))
        }
        
        return files_info
        
    except DatasetNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error listing files for dataset {dataset_name}: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to list dataset files: {str(e)}",
            error_code="DATASET_FILES_ERROR"
        )


@router.get(
    "/{dataset_name}/details",
    response_model=dict,
    summary="Get detailed dataset information",
    description="""
    Get comprehensive dataset details including image information,
    resolutions, captions, and statistics.
    """
)
async def get_dataset_details(
    dataset_name: str = PathParam(..., description="Dataset name"),
    pipeline = Depends(get_pipeline_service)
) -> dict:
    """Get detailed dataset information with image analysis."""
    dataset_name = validate_dataset_name(dataset_name)
    logger.info(f"Getting detailed info for dataset: {dataset_name}")
    
    try:
        # Get dataset path
        input_path = Path(pipeline.base_path) / "workspace" / "input" / dataset_name
        
        if not input_path.exists() or not input_path.is_dir():
            raise DatasetNotFoundError(dataset_name)
        
        # Analyze images and captions
        images_info = []
        stats = {
            "min_width": float('inf'),
            "max_width": 0,
            "min_height": float('inf'),
            "max_height": 0,
            "total_width": 0,
            "total_height": 0,
            "total_size_mb": 0
        }
        
        image_files = [f for f in input_path.iterdir() 
                      if f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}]
        
        for img_file in image_files:
            try:
                # Get image info
                with Image.open(img_file) as img:
                    width, height = img.size
                
                # Check for caption file
                caption_file = img_file.with_suffix('.txt')
                has_caption = caption_file.exists()
                caption = ""
                
                if has_caption:
                    with open(caption_file, 'r', encoding='utf-8') as f:
                        caption = f.read().strip()
                
                # File size
                size = img_file.stat().st_size
                
                # Update stats
                stats["min_width"] = min(stats["min_width"], width)
                stats["max_width"] = max(stats["max_width"], width)
                stats["min_height"] = min(stats["min_height"], height)
                stats["max_height"] = max(stats["max_height"], height)
                stats["total_width"] += width
                stats["total_height"] += height
                stats["total_size_mb"] += size / (1024 * 1024)
                
                images_info.append({
                    "filename": img_file.name,
                    "path": str(img_file),
                    "width": width,
                    "height": height,
                    "size": size,
                    "has_caption": has_caption,
                    "caption": caption if has_caption else None
                })
                
            except Exception as e:
                logger.error(f"Error processing image {img_file}: {e}")
        
        # Calculate averages
        if images_info:
            stats["avg_width"] = int(stats["total_width"] / len(images_info))
            stats["avg_height"] = int(stats["total_height"] / len(images_info))
        else:
            stats["min_width"] = 0
            stats["min_height"] = 0
            stats["avg_width"] = 0
            stats["avg_height"] = 0
        
        # Count captions
        images_with_captions = sum(1 for img in images_info if img["has_caption"])
        images_without_captions = len(images_info) - images_with_captions
        
        return {
            "name": dataset_name,
            "path": str(input_path),
            "total_images": len(images_info),
            "total_texts": len([f for f in input_path.glob("*.txt")]),
            "images_with_captions": images_with_captions,
            "images_without_captions": images_without_captions,
            "images": images_info,
            "stats": {
                "min_width": stats["min_width"],
                "max_width": stats["max_width"],
                "min_height": stats["min_height"],
                "max_height": stats["max_height"],
                "avg_width": stats["avg_width"],
                "avg_height": stats["avg_height"],
                "total_size_mb": round(stats["total_size_mb"], 2)
            }
        }
        
    except DatasetNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting dataset details: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to get dataset details: {str(e)}",
            error_code="DATASET_DETAILS_ERROR"
        )


@router.get(
    "/{dataset_name}/images/{image_name}",
    summary="Get dataset image",
    description="Serve an image file from a dataset"
)
async def get_dataset_image(
    dataset_name: str = PathParam(..., description="Dataset name"),
    image_name: str = PathParam(..., description="Image filename"),
    pipeline = Depends(get_pipeline_service)
):
    """Serve an image from a dataset."""
    dataset_name = validate_dataset_name(dataset_name)
    
    try:
        # Build image path
        image_path = Path(pipeline.base_path) / "workspace" / "input" / dataset_name / image_name
        
        # Security check - ensure the path is within the dataset directory
        dataset_path = Path(pipeline.base_path) / "workspace" / "input" / dataset_name
        if not str(image_path.resolve()).startswith(str(dataset_path.resolve())):
            raise AutoTrainXAPIException(
                message="Invalid image path",
                error_code="INVALID_PATH"
            )
        
        if not image_path.exists() or not image_path.is_file():
            raise AutoTrainXAPIException(
                message=f"Image not found: {image_name}",
                error_code="IMAGE_NOT_FOUND"
            )
        
        # Serve the image
        return FileResponse(
            path=str(image_path),
            media_type=f"image/{image_path.suffix[1:]}"  # Remove the dot from suffix
        )
        
    except AutoTrainXAPIException:
        raise
    except Exception as e:
        logger.error(f"Error serving image: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to serve image: {str(e)}",
            error_code="IMAGE_SERVE_ERROR"
        )


@router.get(
    "/{dataset_name}/sample-prompts",
    response_model=dict,
    summary="Get dataset sample prompts",
    description="""
    Retrieve sample prompts for a dataset.
    
    Returns the sample prompts file content if available,
    which can be used for testing and validation of the trained model.
    """
)
async def get_sample_prompts(
    dataset_name: str = PathParam(..., description="Dataset name"),
    pipeline = Depends(get_pipeline_service)
) -> dict:
    """Get sample prompts for a dataset."""
    dataset_name = validate_dataset_name(dataset_name)
    
    try:
        # Get dataset info
        dataset_info = pipeline.get_dataset_info(dataset_name)
        if not dataset_info:
            raise DatasetNotFoundError(dataset_name)
        
        if not dataset_info["has_sample_prompts"]:
            return {
                "dataset_name": dataset_name,
                "has_sample_prompts": False,
                "prompts": [],
                "message": "No sample prompts available for this dataset"
            }
        
        # Read sample prompts file
        prompts_file = Path(dataset_info["sample_prompts_file"])
        if prompts_file.exists():
            with open(prompts_file, 'r', encoding='utf-8') as f:
                prompts = [line.strip() for line in f.readlines() if line.strip()]
        else:
            prompts = []
        
        return {
            "dataset_name": dataset_name,
            "has_sample_prompts": True,
            "prompts": prompts,
            "total_prompts": len(prompts),
            "prompts_file": str(prompts_file)
        }
        
    except DatasetNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting sample prompts for {dataset_name}: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to get sample prompts: {str(e)}",
            error_code="SAMPLE_PROMPTS_ERROR"
        )


# Health check endpoint for datasets router
@router.get(
    "/health",
    response_model=dict,
    tags=["health"],
    summary="Dataset service health check"
)
async def datasets_health_check(
    pipeline = Depends(get_pipeline_service)
) -> dict:
    """Check health of dataset service."""
    try:
        # Try to list datasets
        prepared_datasets = pipeline.list_prepared_datasets()
        
        # Check workspace paths
        workspace_path = Path(pipeline.base_path) / "workspace"
        input_path = workspace_path / "input"
        output_path = workspace_path / "output"
        
        return {
            "status": "healthy",
            "service": "datasets",
            "dataset_counts": {
                "prepared_datasets": len(prepared_datasets),
                "input_path_exists": input_path.exists(),
                "output_path_exists": output_path.exists()
            },
            "workspace_paths": {
                "workspace": str(workspace_path),
                "input": str(input_path),
                "output": str(output_path)
            },
            "message": "Dataset service is operational"
        }
        
    except Exception as e:
        logger.error(f"Dataset service health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "datasets",
                "error": str(e),
                "message": "Dataset service is not operational"
            }
        )
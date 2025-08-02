"""
Preset configuration API routes.

This module provides REST endpoints for managing training presets,
including listing available presets, viewing configurations, and
generating custom preset configurations.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path
import json
import toml

from fastapi import APIRouter, Depends, Query, Path as PathParam, status
from fastapi.responses import JSONResponse

from ..models.schemas import (
    PresetInfo, PresetListResponse, PresetConfigRequest, PresetConfigResponse,
    BaseResponse
)
from ..dependencies import get_pipeline_service, validate_preset_name, validate_dataset_name
from ..exceptions import (
    PresetNotFoundError, DatasetNotFoundError, ConfigurationError, AutoTrainXAPIException
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/",
    response_model=PresetListResponse,
    summary="List available presets",
    description="""
    Retrieve a list of all available training presets.
    
    Presets are pre-configured training settings for different model
    architectures and training approaches. Each preset includes:
    
    **Preset Types:**
    - **FluxLORA**: FLUX model with LoRA training
    - **FluxCheckpoint**: FLUX model checkpoint training
    - **SDXLCheckpoint**: Stable Diffusion XL checkpoint training
    - **Custom**: User-defined custom presets
    
    **Information Included:**
    - Preset name and description
    - Model architecture and category
    - Available configuration files
    - Usage recommendations
    """
)
async def list_presets(
    category: Optional[str] = Query(None, description="Filter by category: 'base', 'custom', or 'all'"),
    architecture: Optional[str] = Query(None, description="Filter by architecture: 'flux', 'sdxl', etc."),
    pipeline = Depends(get_pipeline_service)
) -> PresetListResponse:
    """List available training presets."""
    logger.info(f"Listing presets with category: {category}, architecture: {architecture}")
    
    try:
        # Get presets from pipeline
        presets_dict = pipeline.list_available_presets()
        presets = []
        
        for preset_name, description in presets_dict.items():
            # Determine category and architecture from preset name
            preset_category = "custom" if preset_name.startswith("custom_") else "base"
            preset_architecture = None
            
            if "flux" in preset_name.lower():
                preset_architecture = "flux"
            elif "sdxl" in preset_name.lower():
                preset_architecture = "sdxl"
            
            # Apply filters
            if category and category != "all" and preset_category != category:
                continue
            if architecture and preset_architecture != architecture.lower():
                continue
            
            # Get configuration files
            config_files = []
            preset_path = Path(pipeline.base_path) / "Presets" / "Base" / preset_name
            if preset_path.exists():
                config_files = [f.name for f in preset_path.iterdir() if f.suffix == ".toml"]
            
            presets.append(PresetInfo(
                name=preset_name,
                description=description,
                category=preset_category,
                architecture=preset_architecture,
                config_files=config_files
            ))
        
        logger.info(f"Found {len(presets)} presets matching filters")
        
        return PresetListResponse(
            success=True,
            message=f"Retrieved {len(presets)} presets",
            presets=presets
        )
        
    except Exception as e:
        logger.error(f"Error listing presets: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to list presets: {str(e)}",
            error_code="PRESET_LIST_ERROR"
        )


@router.get(
    "/{preset_name}",
    response_model=dict,
    summary="Get preset details",
    description="""
    Retrieve detailed information about a specific preset.
    
    Returns comprehensive preset information including:
    - Configuration file contents
    - Parameter descriptions and default values  
    - Model architecture details
    - Usage examples and recommendations
    """
)
async def get_preset(
    preset_name: str = PathParam(..., description="Preset name"),
    include_config: bool = Query(True, description="Include configuration file contents"),
    pipeline = Depends(get_pipeline_service)
) -> dict:
    """Get detailed information about a specific preset."""
    preset_name = validate_preset_name(preset_name)
    logger.info(f"Retrieving preset: {preset_name}")
    
    try:
        # Check if preset exists
        presets_dict = pipeline.list_available_presets()
        if preset_name not in presets_dict:
            raise PresetNotFoundError(preset_name)
        
        # Get preset directory
        preset_path = Path(pipeline.base_path) / "Presets" / "Base" / preset_name
        if not preset_path.exists():
            # Check custom presets
            preset_path = Path(pipeline.base_path) / "Presets" / "Custom" / preset_name
            if not preset_path.exists():
                raise PresetNotFoundError(preset_name)
        
        preset_info = {
            "name": preset_name,
            "description": presets_dict[preset_name],
            "path": str(preset_path),
            "category": "custom" if "Custom" in str(preset_path) else "base",
            "config_files": []
        }
        
        # Get configuration files
        config_contents = {}
        for config_file in preset_path.iterdir():
            if config_file.suffix == ".toml":
                preset_info["config_files"].append(config_file.name)
                
                if include_config:
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config_contents[config_file.name] = toml.load(f)
                    except Exception as e:
                        logger.warning(f"Failed to load config file {config_file}: {e}")
                        config_contents[config_file.name] = {"error": f"Failed to load: {str(e)}"}
        
        if config_contents:
            preset_info["configurations"] = config_contents
        
        # Add metadata based on preset name
        if "flux" in preset_name.lower():
            preset_info["architecture"] = "flux"
            preset_info["model_type"] = "diffusion"
        elif "sdxl" in preset_name.lower():
            preset_info["architecture"] = "sdxl"
            preset_info["model_type"] = "diffusion"
        
        if "lora" in preset_name.lower():
            preset_info["training_type"] = "lora"
        elif "checkpoint" in preset_name.lower():
            preset_info["training_type"] = "checkpoint"
        
        return preset_info
        
    except PresetNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error retrieving preset {preset_name}: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to retrieve preset: {str(e)}",
            error_code="PRESET_RETRIEVAL_ERROR"
        )


@router.post(
    "/generate-config",
    response_model=PresetConfigResponse,
    summary="Generate preset configuration",
    description="""
    Generate a training configuration for a specific dataset and preset.
    
    This endpoint creates a customized training configuration by combining
    the base preset settings with dataset-specific parameters.
    
    **Process:**
    1. Load base preset configuration
    2. Apply dataset-specific settings
    3. Merge with any custom parameters
    4. Generate final training configuration
    5. Save configuration file to workspace
    
    **Custom Parameters:**
    You can override any preset parameter by providing custom values.
    Common parameters to customize:
    - learning_rate: Training learning rate
    - batch_size: Training batch size
    - max_epochs: Maximum training epochs
    - network_dim: Network dimension (for LoRA)
    - network_alpha: Network alpha value (for LoRA)
    """
)
async def generate_preset_config(
    request: PresetConfigRequest,
    pipeline = Depends(get_pipeline_service)
) -> PresetConfigResponse:
    """Generate a training configuration for a dataset and preset."""
    logger.info(f"Generating config for dataset: {request.dataset_name}, preset: {request.preset_name}")
    
    try:
        # Validate dataset exists
        dataset_info = pipeline.get_dataset_info(request.dataset_name)
        if not dataset_info:
            raise DatasetNotFoundError(request.dataset_name)
        
        # Validate preset exists
        presets_dict = pipeline.list_available_presets()
        if request.preset_name not in presets_dict:
            raise PresetNotFoundError(request.preset_name)
        
        # Generate configurations using pipeline
        result = pipeline.generate_configs_only(request.dataset_name)
        
        if result.status.name != "SUCCESS":
            raise ConfigurationError(
                "preset_generation",
                result.error_message or "Configuration generation failed"
            )
        
        # Find the generated configuration file
        workspace_presets = Path(pipeline.base_path) / "workspace" / "Presets"
        config_files = list(workspace_presets.glob(f"{request.dataset_name}_*.toml"))
        
        if not config_files:
            raise ConfigurationError(
                "preset_generation",
                "No configuration file was generated"
            )
        
        # Use the first generated config file
        config_file = config_files[0]
        
        # Load and potentially modify the configuration
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_content = toml.load(f)
            
            # Apply custom parameters if provided
            if request.custom_params:
                for key, value in request.custom_params.items():
                    if '.' in key:
                        # Handle nested keys like "network.dim"
                        keys = key.split('.')
                        current = config_content
                        for k in keys[:-1]:
                            if k not in current:
                                current[k] = {}
                            current = current[k]
                        current[keys[-1]] = value
                    else:
                        config_content[key] = value
                
                # Save modified configuration
                with open(config_file, 'w', encoding='utf-8') as f:
                    toml.dump(config_content, f)
                
                logger.info(f"Applied {len(request.custom_params)} custom parameters")
            
        except Exception as e:
            logger.error(f"Error processing configuration file: {e}")
            raise ConfigurationError(
                "config_processing",
                f"Failed to process configuration: {str(e)}"
            )
        
        return PresetConfigResponse(
            success=True,
            message=f"Configuration generated successfully for {request.dataset_name}",
            config_path=str(config_file),
            config_content=config_content
        )
        
    except (DatasetNotFoundError, PresetNotFoundError, ConfigurationError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating config: {e}")
        raise ConfigurationError(
            "config_generation",
            f"Unexpected error: {str(e)}"
        )


@router.get(
    "/{preset_name}/parameters",
    response_model=dict,
    summary="Get preset parameters",
    description="""
    Get detailed information about parameters available in a preset.
    
    Returns parameter definitions including:
    - Parameter names and types
    - Default values and ranges
    - Descriptions and usage notes
    - Validation constraints
    """
)
async def get_preset_parameters(
    preset_name: str = PathParam(..., description="Preset name"),
    pipeline = Depends(get_pipeline_service)
) -> dict:
    """Get parameter information for a preset."""
    preset_name = validate_preset_name(preset_name)
    
    try:
        # Get preset configuration
        preset_info = await get_preset(preset_name, include_config=True, pipeline=pipeline)
        
        if "configurations" not in preset_info:
            return {
                "preset_name": preset_name,
                "parameters": {},
                "message": "No configuration files found for this preset"
            }
        
        # Extract parameters from configuration files
        all_parameters = {}
        
        for config_name, config_data in preset_info["configurations"].items():
            if isinstance(config_data, dict) and "error" not in config_data:
                parameters = _extract_parameters_from_config(config_data)
                all_parameters[config_name] = parameters
        
        return {
            "preset_name": preset_name,
            "parameters": all_parameters,
            "total_parameters": sum(len(params) for params in all_parameters.values()),
            "config_files": list(all_parameters.keys())
        }
        
    except Exception as e:
        logger.error(f"Error getting parameters for preset {preset_name}: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to get preset parameters: {str(e)}",
            error_code="PRESET_PARAMETERS_ERROR"
        )


@router.get(
    "/categories",
    response_model=dict,
    summary="Get preset categories",
    description="""
    Get information about available preset categories and their characteristics.
    
    Returns category information including:
    - Category names and descriptions
    - Number of presets in each category
    - Supported architectures
    - Usage recommendations
    """
)
async def get_preset_categories(
    pipeline = Depends(get_pipeline_service)
) -> dict:
    """Get information about preset categories."""
    try:
        presets_dict = pipeline.list_available_presets()
        
        categories = {
            "base": {
                "name": "Base Presets",
                "description": "Built-in presets for common training scenarios",
                "presets": [],
                "architectures": set()
            },
            "custom": {
                "name": "Custom Presets",
                "description": "User-defined custom training configurations",
                "presets": [],
                "architectures": set()
            }
        }
        
        for preset_name in presets_dict.keys():
            # Determine category
            category = "custom" if preset_name.startswith("custom_") else "base"
            categories[category]["presets"].append(preset_name)
            
            # Determine architecture
            if "flux" in preset_name.lower():
                categories[category]["architectures"].add("flux")
            elif "sdxl" in preset_name.lower():
                categories[category]["architectures"].add("sdxl")
        
        # Convert sets to lists for JSON serialization
        for category_info in categories.values():
            category_info["architectures"] = list(category_info["architectures"])
            category_info["count"] = len(category_info["presets"])
        
        return {
            "categories": categories,
            "total_presets": len(presets_dict),
            "category_counts": {
                name: info["count"] for name, info in categories.items()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting preset categories: {e}")
        raise AutoTrainXAPIException(
            message=f"Failed to get preset categories: {str(e)}",
            error_code="PRESET_CATEGORIES_ERROR"
        )


def _extract_parameters_from_config(config_data: dict, prefix: str = "") -> dict:
    """
    Extract parameters from configuration data.
    
    Args:
        config_data: Configuration dictionary
        prefix: Prefix for nested keys
        
    Returns:
        Dictionary of parameters with metadata
    """
    parameters = {}
    
    for key, value in config_data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        
        if isinstance(value, dict):
            # Recursively extract from nested dictionaries
            nested_params = _extract_parameters_from_config(value, full_key)
            parameters.update(nested_params)
        else:
            # Add parameter information
            param_info = {
                "value": value,
                "type": type(value).__name__,
                "description": _get_parameter_description(key),
                "category": _get_parameter_category(key),
                "editable": _is_parameter_editable(key)
            }
            
            # Add range information for numeric parameters
            if isinstance(value, (int, float)):
                param_info["range"] = _get_parameter_range(key)
            
            parameters[full_key] = param_info
    
    return parameters


def _get_parameter_description(param_name: str) -> str:
    """Get description for a parameter."""
    descriptions = {
        "learning_rate": "Learning rate for training optimization",
        "batch_size": "Number of samples processed in each training batch",
        "max_epochs": "Maximum number of training epochs",
        "network_dim": "Dimension of the LoRA network layers",
        "network_alpha": "Alpha value for LoRA scaling",
        "resolution": "Training image resolution",
        "save_every_n_epochs": "Save model checkpoint every N epochs",
        "sample_every_n_epochs": "Generate samples every N epochs",
        "clip_skip": "Number of CLIP layers to skip",
    }
    return descriptions.get(param_name, f"Configuration parameter: {param_name}")


def _get_parameter_category(param_name: str) -> str:
    """Get category for a parameter."""
    categories = {
        "learning_rate": "optimization",
        "batch_size": "training",
        "max_epochs": "training",
        "network_dim": "architecture",
        "network_alpha": "architecture",
        "resolution": "data",
        "save_every_n_epochs": "checkpointing",
        "sample_every_n_epochs": "validation",
        "clip_skip": "model",
    }
    return categories.get(param_name, "general")


def _is_parameter_editable(param_name: str) -> bool:
    """Check if a parameter is editable by users."""
    # Most parameters are editable, except system paths and model names
    non_editable = {"model_name", "pretrained_model_name_or_path", "output_dir"}
    return param_name not in non_editable


def _get_parameter_range(param_name: str) -> Optional[dict]:
    """Get valid range for numeric parameters."""
    ranges = {
        "learning_rate": {"min": 1e-6, "max": 1e-2, "suggested": [1e-5, 1e-4, 1e-3]},
        "batch_size": {"min": 1, "max": 32, "suggested": [1, 2, 4, 8]},
        "max_epochs": {"min": 1, "max": 1000, "suggested": [10, 20, 50, 100]},
        "network_dim": {"min": 4, "max": 512, "suggested": [16, 32, 64, 128]},
        "network_alpha": {"min": 1, "max": 512, "suggested": [16, 32, 64]},
        "clip_skip": {"min": 1, "max": 12, "suggested": [1, 2]},
    }
    return ranges.get(param_name)


# Health check endpoint for presets router
@router.get(
    "/health",
    response_model=dict,
    tags=["health"],
    summary="Preset service health check"
)
async def presets_health_check(
    pipeline = Depends(get_pipeline_service)
) -> dict:
    """Check health of preset service."""
    try:
        # Try to list presets
        presets_dict = pipeline.list_available_presets()
        
        # Check preset directories
        base_presets_path = Path(pipeline.base_path) / "Presets" / "Base"
        custom_presets_path = Path(pipeline.base_path) / "Presets" / "Custom"
        
        return {
            "status": "healthy",
            "service": "presets",
            "preset_counts": {
                "total_presets": len(presets_dict),
                "base_presets_path_exists": base_presets_path.exists(),
                "custom_presets_path_exists": custom_presets_path.exists()
            },
            "preset_paths": {
                "base": str(base_presets_path),
                "custom": str(custom_presets_path)
            },
            "available_presets": list(presets_dict.keys()),
            "message": "Preset service is operational"
        }
        
    except Exception as e:
        logger.error(f"Preset service health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "presets",
                "error": str(e),
                "message": "Preset service is not operational"
            }
        )
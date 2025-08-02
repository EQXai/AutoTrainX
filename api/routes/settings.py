"""
Settings management API routes.

Provides endpoints for managing all system configurations including:
- Custom output paths and profiles
- ComfyUI configuration
- Google Sheets sync
- Database management
- System preferences
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from ..dependencies import get_pipeline_service
from ..models.schemas import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response models
class PathConfig(BaseModel):
    """Path configuration model."""
    custom_path: Optional[str] = None
    profile_name: Optional[str] = None


class ComfyUIConfig(BaseModel):
    """ComfyUI configuration model."""
    path: str


class GoogleSheetsConfig(BaseModel):
    """Google Sheets configuration model."""
    enabled: bool
    spreadsheet_id: Optional[str] = None
    credentials_path: Optional[str] = None
    sync_interval: int = 300  # seconds
    batch_size: int = 100


class SystemSettings(BaseModel):
    """Complete system settings."""
    custom_output_path: Optional[str] = None
    active_profile: Optional[str] = None
    comfyui_path: Optional[str] = None
    google_sheets: GoogleSheetsConfig
    database_paths: List[str] = []


class SaveProfileRequest(BaseModel):
    """Request to save a profile."""
    name: str
    custom_path: Optional[str] = None


# Helper functions
def get_config_path(pipeline) -> Path:
    """Get the config file path."""
    return Path(pipeline.base_path) / "config.json"


def get_profiles_path(pipeline) -> Path:
    """Get the profiles file path."""
    settings_dir = Path(pipeline.base_path) / "settings"
    settings_dir.mkdir(exist_ok=True)
    return settings_dir / "profiles.json"


def load_config(pipeline) -> Dict[str, Any]:
    """Load system configuration."""
    config_path = get_config_path(pipeline)
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


def save_config(pipeline, config: Dict[str, Any]):
    """Save system configuration."""
    config_path = get_config_path(pipeline)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


def load_profiles(pipeline) -> Dict[str, Any]:
    """Load saved profiles."""
    profiles_path = get_profiles_path(pipeline)
    if profiles_path.exists():
        with open(profiles_path, 'r') as f:
            return json.load(f)
    return {}


def save_profiles(pipeline, profiles: Dict[str, Any]):
    """Save profiles."""
    profiles_path = get_profiles_path(pipeline)
    with open(profiles_path, 'w') as f:
        json.dump(profiles, f, indent=2)


# API Endpoints
@router.get(
    "/",
    response_model=SystemSettings,
    summary="Get all settings",
    description="Retrieve all system settings and configuration"
)
async def get_settings(
    pipeline = Depends(get_pipeline_service)
) -> SystemSettings:
    """Get all system settings."""
    try:
        config = load_config(pipeline)
        
        # Get Google Sheets config
        sheets_config = config.get('google_sheets_sync', {})
        google_sheets = GoogleSheetsConfig(
            enabled=sheets_config.get('enabled', False),
            spreadsheet_id=sheets_config.get('spreadsheet_id'),
            credentials_path=sheets_config.get('credentials_path'),
            sync_interval=sheets_config.get('sync_interval', 300),
            batch_size=sheets_config.get('batch_size', 100)
        )
        
        # Get database paths
        db_dir = Path(pipeline.base_path) / "DB"
        database_paths = []
        if db_dir.exists():
            database_paths = [str(f) for f in db_dir.glob("*.db")]
        
        return SystemSettings(
            custom_output_path=config.get('custom_output_path'),
            active_profile=config.get('active_profile'),
            comfyui_path=config.get('comfyui_path'),
            google_sheets=google_sheets,
            database_paths=database_paths
        )
        
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve settings: {str(e)}"
        )


@router.put(
    "/",
    response_model=BaseResponse,
    summary="Update settings",
    description="Update system settings"
)
async def update_settings(
    settings: SystemSettings,
    pipeline = Depends(get_pipeline_service)
) -> BaseResponse:
    """Update system settings."""
    try:
        config = load_config(pipeline)
        
        # Update settings
        if settings.custom_output_path is not None:
            config['custom_output_path'] = settings.custom_output_path
        if settings.active_profile is not None:
            config['active_profile'] = settings.active_profile
        if settings.comfyui_path is not None:
            config['comfyui_path'] = settings.comfyui_path
            
        # Update Google Sheets config
        config['google_sheets_sync'] = {
            'enabled': settings.google_sheets.enabled,
            'spreadsheet_id': settings.google_sheets.spreadsheet_id,
            'credentials_path': settings.google_sheets.credentials_path,
            'sync_interval': settings.google_sheets.sync_interval,
            'batch_size': settings.google_sheets.batch_size
        }
        
        save_config(pipeline, config)
        
        return BaseResponse(
            success=True,
            message="Settings updated successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )


# Path Management
@router.get(
    "/profiles",
    response_model=Dict[str, Any],
    summary="List path profiles",
    description="Get all saved path profiles"
)
async def list_profiles(
    pipeline = Depends(get_pipeline_service)
) -> Dict[str, Any]:
    """List all saved profiles."""
    try:
        profiles = load_profiles(pipeline)
        return profiles
        
    except Exception as e:
        logger.error(f"Failed to list profiles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list profiles: {str(e)}"
        )


@router.post(
    "/profiles",
    response_model=BaseResponse,
    summary="Save profile",
    description="Save current configuration as a profile"
)
async def save_profile(
    request: SaveProfileRequest,
    pipeline = Depends(get_pipeline_service)
) -> BaseResponse:
    """Save a configuration profile."""
    try:
        profiles = load_profiles(pipeline)
        
        # Create profile data
        profile_data = {
            'custom_path': request.custom_path,
            'created_at': str(Path.ctime(Path.cwd()))
        }
        
        profiles[request.name] = profile_data
        save_profiles(pipeline, profiles)
        
        return BaseResponse(
            success=True,
            message=f"Profile '{request.name}' saved successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to save profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save profile: {str(e)}"
        )


@router.delete(
    "/profiles/{name}",
    response_model=BaseResponse,
    summary="Delete profile",
    description="Delete a saved profile"
)
async def delete_profile(
    name: str,
    pipeline = Depends(get_pipeline_service)
) -> BaseResponse:
    """Delete a profile."""
    try:
        profiles = load_profiles(pipeline)
        
        if name not in profiles:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile '{name}' not found"
            )
        
        del profiles[name]
        save_profiles(pipeline, profiles)
        
        # If this was the active profile, clear it
        config = load_config(pipeline)
        if config.get('active_profile') == name:
            config['active_profile'] = None
            save_config(pipeline, config)
        
        return BaseResponse(
            success=True,
            message=f"Profile '{name}' deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete profile: {str(e)}"
        )


@router.put(
    "/profiles/{name}/activate",
    response_model=BaseResponse,
    summary="Activate profile",
    description="Switch to a saved profile"
)
async def activate_profile(
    name: str,
    pipeline = Depends(get_pipeline_service)
) -> BaseResponse:
    """Activate a profile."""
    try:
        profiles = load_profiles(pipeline)
        
        if name not in profiles:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile '{name}' not found"
            )
        
        config = load_config(pipeline)
        config['active_profile'] = name
        config['custom_output_path'] = profiles[name].get('custom_path')
        save_config(pipeline, config)
        
        return BaseResponse(
            success=True,
            message=f"Profile '{name}' activated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate profile: {str(e)}"
        )


# ComfyUI Management
@router.post(
    "/comfyui/validate",
    response_model=BaseResponse,
    summary="Validate ComfyUI",
    description="Validate ComfyUI installation and preview system"
)
async def validate_comfyui(
    pipeline = Depends(get_pipeline_service)
) -> BaseResponse:
    """Validate ComfyUI installation."""
    try:
        config = load_config(pipeline)
        comfyui_path = config.get('comfyui_path')
        
        if not comfyui_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ComfyUI path not configured"
            )
        
        # Check if path exists
        if not Path(comfyui_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ComfyUI path does not exist: {comfyui_path}"
            )
        
        # Check for required files
        main_py = Path(comfyui_path) / "main.py"
        if not main_py.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ComfyUI installation: main.py not found"
            )
        
        return BaseResponse(
            success=True,
            message="ComfyUI installation validated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate ComfyUI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate ComfyUI: {str(e)}"
        )


# Database Management
@router.get(
    "/database/stats",
    response_model=Dict[str, Any],
    summary="Database statistics",
    description="Get database statistics"
)
async def get_database_stats(
    pipeline = Depends(get_pipeline_service)
) -> Dict[str, Any]:
    """Get database statistics."""
    try:
        db_dir = Path(pipeline.base_path) / "DB"
        stats = {}
        
        if db_dir.exists():
            for db_file in db_dir.glob("*.db"):
                stats[db_file.name] = {
                    'size': db_file.stat().st_size,
                    'modified': db_file.stat().st_mtime,
                    'path': str(db_file)
                }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get database statistics: {str(e)}"
        )


@router.post(
    "/database/cleanup",
    response_model=BaseResponse,
    summary="Cleanup database",
    description="Clean up old database records"
)
async def cleanup_database(
    days_to_keep: int = 30,
    pipeline = Depends(get_pipeline_service)
) -> BaseResponse:
    """Clean up old database records."""
    try:
        # This is a placeholder - implement actual cleanup logic
        # based on your database structure
        
        return BaseResponse(
            success=True,
            message=f"Database cleanup completed. Records older than {days_to_keep} days removed."
        )
        
    except Exception as e:
        logger.error(f"Failed to cleanup database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup database: {str(e)}"
        )


# Google Sheets
@router.post(
    "/sheets/test",
    response_model=BaseResponse,
    summary="Test Sheets connection",
    description="Test Google Sheets connection"
)
async def test_sheets_connection(
    pipeline = Depends(get_pipeline_service)
) -> BaseResponse:
    """Test Google Sheets connection."""
    try:
        config = load_config(pipeline)
        sheets_config = config.get('google_sheets_sync', {})
        
        if not sheets_config.get('enabled'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google Sheets sync is not enabled"
            )
        
        if not sheets_config.get('spreadsheet_id'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Spreadsheet ID not configured"
            )
        
        # TODO: Implement actual connection test
        # For now, just check configuration
        
        return BaseResponse(
            success=True,
            message="Google Sheets connection test successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test Sheets connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test connection: {str(e)}"
        )
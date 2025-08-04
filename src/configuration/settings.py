"""
Centralized configuration management for AutoTrainX
"""
from pydantic import BaseSettings, Field, validator
from typing import Optional, Dict, Any, List
from enum import Enum
import os
from pathlib import Path

class DatabaseType(str, Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class DatabaseConfig(BaseSettings):
    """Database configuration"""
    type: DatabaseType = DatabaseType.SQLITE
    host: str = "localhost"
    port: int = 5432
    name: str = "autotrainx"
    user: str = "autotrainx"
    password: str = Field(default_factory=lambda: os.getenv('DATABASE_PASSWORD') or os.getenv('AUTOTRAINX_DB_PASSWORD', ''))
    path: Optional[Path] = None
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    
    class Config:
        env_prefix = "AUTOTRAINX_DB_"

class TrainingConfig(BaseSettings):
    """Training configuration"""
    max_concurrent_jobs: int = 1
    default_preset: str = "FluxLORA"
    workspace_dir: Path = Path("workspace")
    models_dir: Path = Path("models")
    timeout_minutes: int = 240
    auto_cleanup: bool = True
    
    class Config:
        env_prefix = "AUTOTRAINX_TRAINING_"

class APIConfig(BaseSettings):
    """API configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: List[str] = ["http://localhost:3000"]
    rate_limit: str = "100/minute"
    jwt_secret: Optional[str] = None
    
    class Config:
        env_prefix = "AUTOTRAINX_API_"

class SheetsConfig(BaseSettings):
    """Google Sheets configuration"""
    enabled: bool = False
    credentials_path: Optional[Path] = None
    sheet_id: Optional[str] = None
    sync_interval: int = 60
    
    class Config:
        env_prefix = "AUTOTRAINX_SHEETS_"

class ComfyUIConfig(BaseSettings):
    """ComfyUI configuration"""
    enabled: bool = True
    host: str = "localhost"
    port: int = 8188
    timeout: int = 30
    max_retries: int = 3
    
    class Config:
        env_prefix = "AUTOTRAINX_COMFYUI_"

class AppConfig(BaseSettings):
    """Main application configuration"""
    # Core settings
    environment: str = "development"
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    
    # Component configs
    database: DatabaseConfig = DatabaseConfig()
    training: TrainingConfig = TrainingConfig()
    api: APIConfig = APIConfig()
    sheets: SheetsConfig = SheetsConfig()
    comfyui: ComfyUIConfig = ComfyUIConfig()
    
    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent
    logs_dir: Path = Path("logs")
    temp_dir: Path = Path("temp")
    
    # Performance
    enable_caching: bool = True
    cache_ttl: int = 3600
    
    class Config:
        env_file = "settings/.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @validator("logs_dir", "temp_dir", pre=True)
    def resolve_paths(cls, v, values):
        if isinstance(v, str):
            v = Path(v)
        if not v.is_absolute():
            return values.get("base_dir", Path.cwd()) / v
        return v

# Global config instance
config = AppConfig()

def get_config() -> AppConfig:
    """Get global configuration instance"""
    return config

def reload_config() -> AppConfig:
    """Reload configuration from environment/files"""
    global config
    config = AppConfig()
    return config
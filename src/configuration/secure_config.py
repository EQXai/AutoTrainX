"""
Secure configuration management for AutoTrainX.
Loads sensitive configuration from environment variables.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class SecureConfig:
    """Manages secure configuration loading from environment variables."""
    
    def _require_env(self, var_name: str) -> str:
        """Require an environment variable to be set."""
        value = os.getenv(var_name)
        if not value:
            raise ValueError(f"{var_name} must be set in environment variables")
        return value
    
    def __init__(self, env_file: Optional[Path] = None):
        """
        Initialize secure configuration.
        
        Args:
            env_file: Optional path to .env file. If not provided, looks for .env in project root.
        """
        # Try to load .env file
        if env_file and env_file.exists():
            load_dotenv(env_file)
        else:
            # Look for .env in common locations
            project_root = Path(__file__).parent.parent.parent
            env_locations = [
                project_root / ".env",
                project_root / "settings" / ".env",
                Path.cwd() / ".env"
            ]
            
            for env_path in env_locations:
                if env_path.exists():
                    load_dotenv(env_path)
                    logger.info(f"Loaded environment from {env_path}")
                    break
            else:
                logger.warning("No .env file found. Using system environment variables only.")
    
    @property
    def database_url(self) -> str:
        """Get database URL from environment."""
        from urllib.parse import quote_plus
        
        default_url = "sqlite:///./autotrainx.db"  # Safe default for development
        
        # Check for DATABASE_URL first
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return db_url  # Assume it's already properly encoded
        
        # Build from components
        db_type = os.getenv("DATABASE_TYPE", "sqlite")
        
        if db_type == "postgresql":
            host = os.getenv("DATABASE_HOST", "localhost")
            port = os.getenv("DATABASE_PORT", "5432")
            name = os.getenv("DATABASE_NAME", "autotrainx")
            user = os.getenv("DATABASE_USER", "autotrainx")
            password = os.getenv("DATABASE_PASSWORD")
            
            if not password:
                logger.error("DATABASE_PASSWORD not set in environment!")
                raise ValueError("DATABASE_PASSWORD must be set in environment variables")
            
            # URL encode the password to handle special characters
            encoded_password = quote_plus(password)
            return f"postgresql://{user}:{encoded_password}@{host}:{port}/{name}"
        
        return default_url
    
    def _sanitize_db_url(self, url: str) -> str:
        """Sanitize database URL for logging (hide password)."""
        if "://" in url and "@" in url:
            # Hide password in URL
            parts = url.split("://", 1)
            if len(parts) == 2:
                protocol = parts[0]
                rest = parts[1]
                if "@" in rest:
                    creds, location = rest.split("@", 1)
                    if ":" in creds:
                        user = creds.split(":", 1)[0]
                        return f"{protocol}://{user}:****@{location}"
        return url
    
    @property
    def database_config(self) -> Dict[str, Any]:
        """Get database configuration dictionary."""
        return {
            "type": os.getenv("DATABASE_TYPE", "sqlite"),
            "host": os.getenv("DATABASE_HOST", "localhost"),
            "port": int(os.getenv("DATABASE_PORT", "5432")),
            "name": os.getenv("DATABASE_NAME", "autotrainx"),
            "user": os.getenv("DATABASE_USER", "autotrainx"),
            "password": os.getenv("DATABASE_PASSWORD") or self._require_env("DATABASE_PASSWORD"),
            "pool_size": int(os.getenv("DATABASE_POOL_SIZE", "10")),
            "echo": os.getenv("DATABASE_ECHO", "false").lower() == "true"
        }
    
    @property
    def google_credentials(self) -> Optional[Dict[str, Any]]:
        """
        Get Google service account credentials from environment.
        
        Returns:
            Dictionary with credentials or None if not configured.
        """
        # First check for GOOGLE_APPLICATION_CREDENTIALS file path
        creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_file and Path(creds_file).exists():
            try:
                with open(creds_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load Google credentials from file: {e}")
        
        # Try to build from individual environment variables
        email = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
        private_key = os.getenv("GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY")
        project_id = os.getenv("GOOGLE_PROJECT_ID")
        
        if email and private_key and project_id:
            # Ensure private key has proper line breaks
            if "\\n" in private_key:
                private_key = private_key.replace("\\n", "\n")
            
            return {
                "type": "service_account",
                "project_id": project_id,
                "client_email": email,
                "private_key": private_key,
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{email}"
            }
        
        # Try to load from settings directory as fallback (but log warning)
        settings_path = Path(__file__).parent.parent.parent / "settings" / "google_credentials.json"
        if settings_path.exists():
            logger.warning(
                "Loading Google credentials from settings/google_credentials.json. "
                "This is INSECURE! Please move to environment variables."
            )
            try:
                with open(settings_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load Google credentials: {e}")
        
        return None
    
    @property
    def api_secret_key(self) -> str:
        """Get API secret key for session management."""
        key = os.getenv("API_SECRET_KEY")
        if not key:
            logger.error(
                "API_SECRET_KEY not set in environment! "
                "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
            raise ValueError("API_SECRET_KEY must be set in environment variables")
        return key
    
    @property
    def jwt_config(self) -> Dict[str, Any]:
        """Get JWT configuration for API authentication."""
        return {
            "secret_key": os.getenv("JWT_SECRET_KEY", self.api_secret_key),
            "algorithm": os.getenv("JWT_ALGORITHM", "HS256"),
            "access_token_expire_minutes": int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        }
    
    @property
    def cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration."""
        origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "*")
        if origins_str == "*":
            origins = ["*"]
        else:
            origins = [origin.strip() for origin in origins_str.split(",")]
        
        return {
            "allow_origins": origins,
            "allow_credentials": os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true",
            "allow_methods": os.getenv("CORS_ALLOWED_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(","),
            "allow_headers": os.getenv("CORS_ALLOWED_HEADERS", "*").split(",")
        }
    
    def validate_configuration(self) -> bool:
        """
        Validate that critical configuration is properly set.
        
        Returns:
            True if configuration is valid, False otherwise.
        """
        is_valid = True
        
        # Check database password
        db_password = os.getenv("DATABASE_PASSWORD")
        if not db_password or db_password in ["1234", "password", "changeme", "admin"]:
            logger.error(
                "CRITICAL: Weak or default database password detected! "
                "Please set a strong DATABASE_PASSWORD in your environment."
            )
            is_valid = False
        
        # Check API secret key
        if not os.getenv("API_SECRET_KEY"):
            logger.error(
                "CRITICAL: API_SECRET_KEY not set! "
                "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
            is_valid = False
        
        # Check CORS in production
        if os.getenv("ENVIRONMENT") == "production" and self.cors_config["allow_origins"] == ["*"]:
            logger.error(
                "CRITICAL: CORS allows all origins in production! "
                "Set CORS_ALLOWED_ORIGINS to specific domains."
            )
            is_valid = False
        
        return is_valid


# Global instance
secure_config = SecureConfig()
#!/usr/bin/env python3
"""
AutoTrainX Secure Configuration Setup Script

This script helps you set up secure configuration for AutoTrainX
by creating a proper .env file with strong passwords and secure settings.
"""

import os
import sys
import secrets
import string
import json
from pathlib import Path
from typing import Optional, Dict, Any
import getpass


def generate_secure_password(length: int = 32) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_secret_key() -> str:
    """Generate a secure secret key for API/JWT."""
    return secrets.token_hex(32)


def prompt_for_value(prompt: str, default: Optional[str] = None, is_password: bool = False) -> str:
    """Prompt user for a value with optional default."""
    if default and not is_password:
        prompt_text = f"{prompt} [{default}]: "
    else:
        prompt_text = f"{prompt}: "
    
    if is_password:
        value = getpass.getpass(prompt_text)
    else:
        value = input(prompt_text)
    
    if not value and default:
        return default
    return value.strip()


def setup_database_config() -> Dict[str, str]:
    """Set up database configuration."""
    print("\n=== Database Configuration ===")
    
    db_type = prompt_for_value(
        "Database type (postgresql/sqlite)",
        default="postgresql"
    ).lower()
    
    config = {"DATABASE_TYPE": db_type}
    
    if db_type == "postgresql":
        config["DATABASE_HOST"] = prompt_for_value("Database host", default="localhost")
        config["DATABASE_PORT"] = prompt_for_value("Database port", default="5432")
        config["DATABASE_NAME"] = prompt_for_value("Database name", default="autotrainx")
        config["DATABASE_USER"] = prompt_for_value("Database user", default="autotrainx")
        
        use_generated = prompt_for_value(
            "Generate secure password? (y/n)",
            default="y"
        ).lower() == 'y'
        
        if use_generated:
            password = generate_secure_password()
            print(f"Generated password: {password}")
            print("⚠️  IMPORTANT: Save this password securely! You'll need it for PostgreSQL setup.")
        else:
            password = prompt_for_value("Database password", is_password=True)
        
        config["DATABASE_PASSWORD"] = password
        config["DATABASE_URL"] = f"postgresql://{config['DATABASE_USER']}:{password}@{config['DATABASE_HOST']}:{config['DATABASE_PORT']}/{config['DATABASE_NAME']}"
    else:
        db_path = prompt_for_value("SQLite database path", default="./DB/autotrainx.db")
        config["DATABASE_URL"] = f"sqlite:///{db_path}"
    
    config["DATABASE_POOL_SIZE"] = prompt_for_value("Connection pool size", default="10")
    config["DATABASE_ECHO"] = "false"
    
    return config


def setup_google_credentials() -> Dict[str, str]:
    """Set up Google Cloud credentials configuration."""
    print("\n=== Google Cloud Configuration ===")
    
    use_google = prompt_for_value(
        "Do you want to configure Google Sheets integration? (y/n)",
        default="n"
    ).lower() == 'y'
    
    if not use_google:
        return {}
    
    config = {}
    
    creds_method = prompt_for_value(
        "How do you want to provide credentials?\n"
        "1. Path to JSON file\n"
        "2. Individual values (more secure)\n"
        "Choose (1/2)",
        default="2"
    )
    
    if creds_method == "1":
        json_path = prompt_for_value("Path to service account JSON file")
        if Path(json_path).exists():
            config["GOOGLE_APPLICATION_CREDENTIALS"] = json_path
        else:
            print(f"⚠️  Warning: File {json_path} not found. Please ensure it exists.")
            config["GOOGLE_APPLICATION_CREDENTIALS"] = json_path
    else:
        print("\n📋 Enter Google service account details:")
        config["GOOGLE_SERVICE_ACCOUNT_EMAIL"] = prompt_for_value("Service account email")
        config["GOOGLE_PROJECT_ID"] = prompt_for_value("Google Cloud project ID")
        
        print("\n🔑 Private key (paste the entire key including BEGIN/END lines, then press Enter twice):")
        lines = []
        while True:
            line = input()
            if not line and lines and lines[-1] == "":
                break
            lines.append(line)
        
        private_key = "\\n".join(lines[:-1])  # Remove last empty line
        config["GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY"] = private_key
    
    # Ask for Google Sheets ID
    print("\n📊 Google Sheets Configuration:")
    sheets_id = prompt_for_value(
        "Google Sheets ID (from the spreadsheet URL)",
        default=""
    )
    if sheets_id:
        # Clean the ID in case user pasted the full URL
        if "spreadsheets/d/" in sheets_id:
            sheets_id = sheets_id.split("spreadsheets/d/")[1].split("/")[0]
        config["AUTOTRAINX_SHEETS_ID"] = sheets_id
    else:
        print("⚠️  Warning: No Sheets ID provided. You'll need to configure this later.")
    
    return config


def setup_security_config() -> Dict[str, str]:
    """Set up security configuration."""
    print("\n=== Security Configuration ===")
    
    config = {}
    
    # API Secret Key
    generate_api_key = prompt_for_value(
        "Generate secure API secret key? (y/n)",
        default="y"
    ).lower() == 'y'
    
    if generate_api_key:
        api_key = generate_secret_key()
        print(f"Generated API secret key: {api_key}")
        config["API_SECRET_KEY"] = api_key
    else:
        config["API_SECRET_KEY"] = prompt_for_value("API secret key")
    
    # JWT Configuration
    generate_jwt_key = prompt_for_value(
        "Generate secure JWT secret key? (y/n)",
        default="y"
    ).lower() == 'y'
    
    if generate_jwt_key:
        jwt_key = generate_secret_key()
        print(f"Generated JWT secret key: {jwt_key}")
        config["JWT_SECRET_KEY"] = jwt_key
    else:
        config["JWT_SECRET_KEY"] = prompt_for_value("JWT secret key")
    
    config["JWT_ALGORITHM"] = "HS256"
    config["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = prompt_for_value(
        "JWT token expiration (minutes)",
        default="30"
    )
    
    return config


def setup_cors_config() -> Dict[str, str]:
    """Set up CORS configuration."""
    print("\n=== CORS Configuration ===")
    
    is_production = prompt_for_value(
        "Is this for production? (y/n)",
        default="n"
    ).lower() == 'y'
    
    config = {}
    
    if is_production:
        print("Enter allowed origins (comma-separated, e.g., https://app.example.com,https://api.example.com)")
        origins = prompt_for_value("Allowed origins")
        config["CORS_ALLOWED_ORIGINS"] = origins
    else:
        config["CORS_ALLOWED_ORIGINS"] = "*"
        print("⚠️  Warning: CORS is set to allow all origins. Change this for production!")
    
    config["CORS_ALLOW_CREDENTIALS"] = "true"
    config["CORS_ALLOWED_METHODS"] = "GET,POST,PUT,DELETE,OPTIONS"
    config["CORS_ALLOWED_HEADERS"] = "*"
    
    return config


def write_env_file(config: Dict[str, str], path: Path) -> None:
    """Write configuration to .env file."""
    # Group configurations
    groups = {
        "Database Configuration": [
            "DATABASE_TYPE", "DATABASE_URL", "DATABASE_HOST", "DATABASE_PORT",
            "DATABASE_NAME", "DATABASE_USER", "DATABASE_PASSWORD", 
            "DATABASE_POOL_SIZE", "DATABASE_ECHO"
        ],
        "Google Cloud Configuration": [
            "GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_SERVICE_ACCOUNT_EMAIL",
            "GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY", "GOOGLE_PROJECT_ID",
            "AUTOTRAINX_SHEETS_ID"
        ],
        "Security Configuration": [
            "API_SECRET_KEY", "JWT_SECRET_KEY", "JWT_ALGORITHM",
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
        ],
        "CORS Configuration": [
            "CORS_ALLOWED_ORIGINS", "CORS_ALLOW_CREDENTIALS",
            "CORS_ALLOWED_METHODS", "CORS_ALLOWED_HEADERS"
        ]
    }
    
    with open(path, 'w') as f:
        f.write("# AutoTrainX Secure Configuration\n")
        f.write("# Generated by setup_secure_config.py\n")
        f.write("# ⚠️  KEEP THIS FILE SECRET - DO NOT COMMIT TO VERSION CONTROL\n\n")
        
        for group_name, keys in groups.items():
            # Only write group if it has values
            group_values = [(k, v) for k, v in config.items() if k in keys and v]
            if group_values:
                f.write(f"# {group_name}\n")
                for key, value in group_values:
                    # Handle multiline values (like private keys)
                    if "\\n" in value:
                        f.write(f'{key}="{value}"\n')
                    else:
                        f.write(f"{key}={value}\n")
                f.write("\n")
        
        # Add legacy support for backward compatibility
        if "DATABASE_TYPE" in config:
            f.write("# Legacy support (will be deprecated)\n")
            legacy_mapping = {
                "DATABASE_TYPE": "AUTOTRAINX_DB_TYPE",
                "DATABASE_HOST": "AUTOTRAINX_DB_HOST",
                "DATABASE_PORT": "AUTOTRAINX_DB_PORT",
                "DATABASE_NAME": "AUTOTRAINX_DB_NAME",
                "DATABASE_USER": "AUTOTRAINX_DB_USER",
                "DATABASE_PASSWORD": "AUTOTRAINX_DB_PASSWORD"
            }
            for new_key, legacy_key in legacy_mapping.items():
                if new_key in config:
                    f.write(f"{legacy_key}={config[new_key]}\n")
            f.write("\n")


def main():
    """Main setup function."""
    print("🔒 AutoTrainX Secure Configuration Setup")
    print("=" * 50)
    print("\nThis script will help you create a secure .env configuration file.")
    print("All sensitive values will be stored in the .env file only.\n")
    
    # Check if .env already exists
    env_path = Path(".env")
    if env_path.exists():
        overwrite = prompt_for_value(
            "⚠️  .env file already exists. Overwrite? (y/n)",
            default="n"
        ).lower() == 'y'
        
        if not overwrite:
            print("Setup cancelled.")
            return
    
    # Collect all configuration
    config = {}
    
    # Database configuration
    config.update(setup_database_config())
    
    # Google Cloud configuration
    config.update(setup_google_credentials())
    
    # Security configuration
    config.update(setup_security_config())
    
    # CORS configuration
    config.update(setup_cors_config())
    
    # Write configuration
    write_env_file(config, env_path)
    
    print(f"\n✅ Configuration saved to {env_path}")
    print("\n📋 Next steps:")
    print("1. Review the generated .env file")
    print("2. Ensure .env is in your .gitignore (should be already)")
    print("3. If using PostgreSQL, create the database and user with the generated password")
    print("4. If using Google Sheets, ensure the service account has access to your spreadsheet")
    print("\n🔒 Security reminders:")
    print("- NEVER commit .env to version control")
    print("- Keep backup of passwords in a secure password manager")
    print("- Rotate secrets regularly")
    print("- Use different passwords for different environments")
    
    # Create .env.example if it doesn't exist
    example_path = Path(".env.example")
    if not example_path.exists():
        print(f"\n📝 Creating {example_path} for reference...")
        # Copy from our created example
        src_example = Path(__file__).parent / ".env.example"
        if src_example.exists():
            import shutil
            shutil.copy(src_example, example_path)
            print(f"✅ Created {example_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
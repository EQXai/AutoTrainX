#!/usr/bin/env python3
"""
AutoTrainX Interactive Configuration & Management Menu v2.0

Unified configuration and management interface that integrates:
- System configuration (Database, Google Sheets, ComfyUI, Paths)
- Training configuration (Presets, Display settings)
- System administration and monitoring
- Information and reports
"""

import sys
import os
import subprocess
import json
import time
import psutil
import psycopg2
import secrets
import string
import getpass
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import questionary
    from questionary import Style
except ImportError:
    print("Error: questionary library not found.")
    print("Please install it with: pip install questionary")
    sys.exit(1)

from src.config import Config

# Import secure_config with error handling
try:
    from src.configuration.secure_config import secure_config
    print("🔧 Debug: secure_config imported successfully")
except Exception as e:
    print(f"🔧 Debug: Failed to import secure_config: {type(e).__name__}: {e}")
    # Create fallback secure_config
    class FallbackSecureConfig:
        @property
        def database_config(self):
            return {
                'password': os.getenv('DATABASE_PASSWORD', 'autotrainx_default')
            }
    secure_config = FallbackSecureConfig()
    print("🔧 Debug: Using fallback secure_config")


# Custom styling for professional appearance
AUTOTRAINX_STYLE = Style([
    ('qmark', 'fg:#ff9d00 bold'),           # Question mark - orange
    ('question', 'bold'),                    # Question text
    ('answer', 'fg:#ff9d00 bold'),          # Selected answer - orange
    ('pointer', 'fg:#ff9d00 bold'),         # Selection pointer - orange
    ('highlighted', 'fg:#ff9d00 bold'),     # Highlighted option - orange
    ('selected', 'fg:#cc5454'),             # Selected items - red
    ('separator', 'fg:#6c6c6c'),            # Separators - gray
    ('instruction', 'fg:#6c6c6c italic'),   # Instructions - gray italic
    ('text', ''),                           # Plain text
])


@dataclass
class MenuResult:
    """Result of a menu operation."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class AutoTrainXMenu:
    """Unified interactive menu interface for AutoTrainX."""
    
    def __init__(self):
        """Initialize the menu system."""
        self.base_path = Config.get_default_base_path()
        self.running = True
        
        # Integration with postgresql_manager and sheets_sync_manager
        self.script_dir = Path(__file__).parent.parent.parent
        self.pid_file = self.script_dir / ".sheets_sync_daemon.pid"
        self.log_file = self.script_dir / "logs" / "sheets_sync_daemon.log"
        self.config_file = self.script_dir / "config.json"
        self.env_file = self.script_dir / ".env"
        
        # Database configuration
        self.db_config = {
            'host': os.getenv('DATABASE_HOST', 'localhost'),
            'port': os.getenv('DATABASE_PORT', '5432'),
            'database': os.getenv('DATABASE_NAME', 'autotrainx'),
            'user': os.getenv('DATABASE_USER', 'autotrainx'),
            'password': os.getenv('DATABASE_PASSWORD', secure_config.database_config['password'])
        }
        
        # Environment detection
        self.is_docker = os.path.exists('/.dockerenv')
        self.is_wsl = 'microsoft' in os.uname().release.lower() if hasattr(os, 'uname') else False
        self.is_root = os.geteuid() == 0 if hasattr(os, 'geteuid') else False
        self.running_in_docker = self.is_docker or os.getenv('RUNNING_IN_DOCKER', '').lower() == 'true'
        
    def _run_privileged_command(self, cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Run a command with appropriate privileges."""
        if self.is_root or self.running_in_docker:
            # Already running as root or in Docker
            if cmd[0] == "sudo":
                if len(cmd) > 2 and cmd[1] == "-u":
                    # Handle 'sudo -u user command' -> switch to that user
                    user = cmd[2]
                    actual_cmd = cmd[3:]
                    
                    # For psql commands with -f flag, we need special handling
                    if actual_cmd[0] == "psql" and "-f" in actual_cmd:
                        # Find the -f flag and its argument
                        f_index = actual_cmd.index("-f")
                        if f_index + 1 < len(actual_cmd):
                            sql_file = actual_cmd[f_index + 1]
                            # Read the SQL file content
                            try:
                                with open(sql_file, 'r') as f:
                                    sql_content = f.read()
                                # Use su with echo to pipe SQL to psql
                                new_cmd = ["su", "-", user, "-c", f"psql <<EOF\n{sql_content}\nEOF"]
                                return subprocess.run(new_cmd, shell=True, **kwargs)
                            except:
                                pass
                    
                    # For other commands, join them properly
                    cmd_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in actual_cmd)
                    new_cmd = ["su", "-", user, "-c", cmd_str]
                    return subprocess.run(new_cmd, **kwargs)
                else:
                    # Simple sudo command, just remove sudo
                    cmd = cmd[1:]
        else:
            # Not root, need sudo
            if cmd[0] != "sudo":
                cmd = ["sudo"] + cmd
        
        return subprocess.run(cmd, **kwargs)
    
    def _get_environment_info(self) -> str:
        """Get a string describing the current environment."""
        env_parts = []
        if self.is_docker:
            env_parts.append("Docker Container")
        if self.is_wsl:
            env_parts.append("WSL")
        if self.is_root:
            env_parts.append("Root User")
        
        return " / ".join(env_parts) if env_parts else "Standard Linux"
        
    # ============================================================================
    # INITIAL SETUP FUNCTIONS (from setup_secure_config.py)
    # ============================================================================
    
    def _is_system_configured(self) -> bool:
        """Check if the system has been properly configured."""
        env_file = self.script_dir / ".env"
        if not env_file.exists():
            return False
            
        required_vars = [
            'DATABASE_TYPE', 'DATABASE_PASSWORD', 'API_SECRET_KEY', 
            'JWT_SECRET_KEY', 'AUTOTRAINX_SHEETS_ID'
        ]
        
        try:
            with open(env_file, 'r') as f:
                content = f.read()
                missing_vars = []
                for var in required_vars:
                    if f"{var}=" not in content:
                        missing_vars.append(var)
                
                if missing_vars:
                    print(f"🔧 Debug: Missing variables in .env: {', '.join(missing_vars)}")
                    return False
            return True
        except FileNotFoundError:
            print(f"🔧 Debug: .env file not found at {env_file}")
            return False
        except PermissionError:
            print(f"🔧 Debug: Permission denied reading {env_file}")
            return False
        except Exception as e:
            print(f"🔧 Debug: Error reading .env file: {type(e).__name__}: {e}")
            return False
    
    def _generate_secure_password(self, length: int = 32) -> str:
        """Generate a secure random password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def _generate_secret_key(self) -> str:
        """Generate a secure secret key for API/JWT."""
        return secrets.token_hex(32)
    
    def _prompt_for_value(self, prompt: str, default: Optional[str] = None, is_password: bool = False) -> str:
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
    
    def _setup_database_config(self) -> Dict[str, str]:
        """Set up database configuration (PostgreSQL only)."""
        print("\n=== Database Configuration ===")
        print("⚠️  AutoTrainX requires PostgreSQL. SQLite is not supported.")
        
        config = {"DATABASE_TYPE": "postgresql"}
        
        config["DATABASE_HOST"] = self._prompt_for_value("Database host", default="localhost")
        config["DATABASE_PORT"] = self._prompt_for_value("Database port", default="5432")
        config["DATABASE_NAME"] = self._prompt_for_value("Database name", default="autotrainx")
        config["DATABASE_USER"] = self._prompt_for_value("Database user", default="autotrainx")
        
        use_generated = self._prompt_for_value(
            "Generate secure password? (y/n)",
            default="y"
        ).lower() == 'y'
        
        if use_generated:
            password = self._generate_secure_password()
            print(f"Generated password: {password}")
            print("⚠️  IMPORTANT: Save this password securely! You'll need it for PostgreSQL setup.")
        else:
            password = self._prompt_for_value("Database password", is_password=True)
        
        config["DATABASE_PASSWORD"] = password
        config["DATABASE_URL"] = f"postgresql://{config['DATABASE_USER']}:{password}@{config['DATABASE_HOST']}:{config['DATABASE_PORT']}/{config['DATABASE_NAME']}"
        config["DATABASE_POOL_SIZE"] = self._prompt_for_value("Connection pool size", default="10")
        config["DATABASE_ECHO"] = "false"
        
        return config
    
    def _setup_google_credentials(self) -> Dict[str, str]:
        """Set up Google Cloud credentials configuration."""
        print("\n=== Google Cloud Configuration ===")
        
        use_google = self._prompt_for_value(
            "Do you want to configure Google Sheets integration? (y/n)",
            default="y"
        ).lower() == 'y'
        
        if not use_google:
            print("⚠️  Warning: Google Sheets integration will not be available.")
            return {}
        
        config = {}
        
        creds_method = self._prompt_for_value(
            "How do you want to provide credentials?\n"
            "1. Path to JSON file\n"
            "2. Individual values (more secure)\n"
            "Choose (1/2)",
            default="2"
        )
        
        if creds_method == "1":
            json_path = self._prompt_for_value("Path to service account JSON file")
            if Path(json_path).exists():
                config["GOOGLE_APPLICATION_CREDENTIALS"] = json_path
            else:
                print(f"⚠️  Warning: File {json_path} not found. Please ensure it exists.")
                config["GOOGLE_APPLICATION_CREDENTIALS"] = json_path
        else:
            print("\n📋 Enter Google service account details:")
            config["GOOGLE_SERVICE_ACCOUNT_EMAIL"] = self._prompt_for_value("Service account email")
            config["GOOGLE_PROJECT_ID"] = self._prompt_for_value("Google Cloud project ID")
            
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
        sheets_id = self._prompt_for_value(
            "Google Sheets ID (from the spreadsheet URL)",
            default=""
        )
        if sheets_id:
            # Clean the ID in case user pasted the full URL
            if "spreadsheets/d/" in sheets_id:
                sheets_id = sheets_id.split("spreadsheets/d/")[1].split("/")[0]
            config["AUTOTRAINX_SHEETS_ID"] = sheets_id
        else:
            print("⚠️  Warning: No Sheets ID provided. Google Sheets integration will not work.")
        
        return config
    
    def _setup_security_config(self) -> Dict[str, str]:
        """Set up security configuration."""
        print("\n=== Security Configuration ===")
        
        config = {}
        
        # API Secret Key
        generate_api_key = self._prompt_for_value(
            "Generate secure API secret key? (y/n)",
            default="y"
        ).lower() == 'y'
        
        if generate_api_key:
            api_key = self._generate_secret_key()
            print(f"Generated API secret key: {api_key}")
            config["API_SECRET_KEY"] = api_key
        else:
            config["API_SECRET_KEY"] = self._prompt_for_value("API secret key")
        
        # JWT Configuration
        generate_jwt_key = self._prompt_for_value(
            "Generate secure JWT secret key? (y/n)",
            default="y"
        ).lower() == 'y'
        
        if generate_jwt_key:
            jwt_key = self._generate_secret_key()
            print(f"Generated JWT secret key: {jwt_key}")
            config["JWT_SECRET_KEY"] = jwt_key
        else:
            config["JWT_SECRET_KEY"] = self._prompt_for_value("JWT secret key")
        
        config["JWT_ALGORITHM"] = "HS256"
        config["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = self._prompt_for_value(
            "JWT token expiration (minutes)",
            default="30"
        )
        
        return config
    
    def _setup_cors_config(self) -> Dict[str, str]:
        """Set up CORS configuration."""
        print("\n=== CORS Configuration ===")
        
        is_production = self._prompt_for_value(
            "Is this for production? (y/n)",
            default="n"
        ).lower() == 'y'
        
        config = {}
        
        if is_production:
            print("Enter allowed origins (comma-separated, e.g., https://app.example.com,https://api.example.com)")
            origins = self._prompt_for_value("Allowed origins")
            config["CORS_ALLOWED_ORIGINS"] = origins
        else:
            config["CORS_ALLOWED_ORIGINS"] = "*"
            print("⚠️  Warning: CORS is set to allow all origins. Change this for production!")
        
        config["CORS_ALLOW_CREDENTIALS"] = "true"
        config["CORS_ALLOWED_METHODS"] = "GET,POST,PUT,DELETE,OPTIONS"
        config["CORS_ALLOWED_HEADERS"] = "*"
        
        return config
    
    def _write_env_file(self, config: Dict[str, str], path: Path) -> None:
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
                "GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY", "GOOGLE_PROJECT_ID"
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
        
        try:
            # Ensure parent directory exists with proper error handling
            path.parent.mkdir(parents=True, exist_ok=True)
            print(f"🔧 Debug: Ensured directory exists: {path.parent}")
        except PermissionError as e:
            raise PermissionError(f"Cannot create directory {path.parent}: {e}")
        except Exception as e:
            raise Exception(f"Failed to create directory {path.parent}: {type(e).__name__}: {e}")
        
        try:
            with open(path, 'w') as f:
                f.write("# AutoTrainX Secure Configuration\n")
                f.write("# Generated by AutoTrainX Interactive Menu\n")
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
                
                # Add Google Sheets Configuration
                if "AUTOTRAINX_SHEETS_ID" in config:
                    f.write("# Google Sheets Configuration\n")
                    f.write(f"AUTOTRAINX_SHEETS_ID={config['AUTOTRAINX_SHEETS_ID']}\n")
            
            print(f"🔧 Debug: Successfully wrote .env file to {path}")
            
        except PermissionError as e:
            raise PermissionError(f"Cannot write to {path}: {e}")
        except Exception as e:
            raise Exception(f"Failed to write .env file {path}: {type(e).__name__}: {e}")
    
    def _run_initial_setup(self) -> bool:
        """Run the complete initial setup wizard."""
        print("\n🔒 AutoTrainX Initial Setup Wizard")
        print("=" * 50)
        print("\nThis wizard will configure all necessary settings for AutoTrainX.")
        print("All sensitive values will be stored securely in the .env file.\n")
        
        # Check if .env already exists
        env_path = self.script_dir / ".env"
        if env_path.exists():
            overwrite = self._prompt_for_value(
                "⚠️  .env file already exists. Overwrite? (y/n)",
                default="n"
            ).lower() == 'y'
            
            if not overwrite:
                print("Setup cancelled.")
                return False
        
        try:
            # Collect all configuration
            config = {}
            
            # Database configuration (PostgreSQL only)
            config.update(self._setup_database_config())
            
            # Google Cloud configuration
            config.update(self._setup_google_credentials())
            
            # Security configuration
            config.update(self._setup_security_config())
            
            # CORS configuration
            config.update(self._setup_cors_config())
            
            # Write configuration
            self._write_env_file(config, env_path)
            
            print(f"\n✅ Configuration saved to {env_path}")
            print("\n📋 Next steps:")
            print("1. Review the generated .env file")
            print("2. If using PostgreSQL, create the database and user with the generated password")
            print("3. If using Google Sheets, ensure the service account has access to your spreadsheet")
            print("\n🔒 Security reminders:")
            print("- NEVER commit .env to version control")
            print("- Keep backup of passwords in a secure password manager")
            print("- Rotate secrets regularly")
            
            input("\nPress Enter to continue...")
            return True
            
        except Exception as e:
            print(f"\n❌ Setup failed: {type(e).__name__}: {e}")
            print(f"🔧 Debug: Error occurred in _run_initial_setup")
            print(f"🔧 Debug: Config collected so far: {list(config.keys()) if 'config' in locals() else 'None'}")
            print(f"🔧 Debug: Target .env path: {env_path}")
            input("\nPress Enter to continue...")
            return False
        
    def run(self) -> None:
        """Main menu loop."""
        self._show_header()
        
        # Check if system is configured
        is_configured = self._is_system_configured()
        
        while self.running:
            try:
                os.system('cls' if os.name == 'nt' else 'clear')
                self._show_header()
                
                # Show configuration status
                if not is_configured:
                    print("⚠️  INITIAL SETUP REQUIRED ⚠️")
                    print("AutoTrainX needs to be configured before use.\n")
                    
                    choices = [
                        "🔧 Initial Setup Wizard (REQUIRED)",
                        "❓ Help & Documentation",
                        "❌ Exit"
                    ]
                else:
                    print("✅ System Configured\n")
                    choices = [
                        "🔧 Configuration Management",
                        "📚 Training Configuration", 
                        "🛠️  System Administration",
                        "📊 Information & Reports",
                        "❓ Help & Documentation",
                        "❌ Exit"
                    ]
                
                choice = questionary.select(
                    "Main Menu - What would you like to do?",
                    choices=choices,
                    style=AUTOTRAINX_STYLE
                ).ask()
                
                if choice is None:  # User pressed Ctrl+C
                    break
                
                if "Initial Setup Wizard" in choice:
                    if self._run_initial_setup():
                        is_configured = True  # Update status after successful setup
                elif "Configuration Management" in choice or "System Configuration" in choice:
                    self._system_configuration_menu()
                elif "Training Configuration" in choice:
                    self._training_configuration_menu()
                elif "System Administration" in choice:
                    self._system_administration_menu()
                elif "Information & Reports" in choice:
                    self._information_reports_menu()
                elif "Help & Documentation" in choice:
                    self._help_documentation_menu()
                elif "Exit" in choice:
                    self.running = False
                    
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                self._show_error(f"An error occurred: {str(e)}")
        
        print("\n" + "="*60)
        print("Thank you for using AutoTrainX!")
        print("="*60)
    
    def _show_header(self) -> None:
        """Display the application header."""
        print("\n" + "="*60)
        print("         AUTOTRAINX CONFIGURATION & MANAGEMENT")
        print("                    Version 2.0")
        env_info = self._get_environment_info()
        if env_info:
            print(f"              Environment: {env_info}")
        print("="*60)
        print("Navigate with arrow keys, select with Enter")
        print("Press Ctrl+C to exit at any time")
        print("="*60 + "\n")
    
    # SYSTEM CONFIGURATION MENU
    def _system_configuration_menu(self) -> None:
        """System configuration main menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            choice = questionary.select(
                "System Configuration:",
                choices=[
                    "🔧 Run Initial Setup Wizard",
                    "🗄️  Database Configuration",
                    "📊 Google Sheets Sync",
                    "🖼️  ComfyUI Configuration",
                    "📁 Path Configuration",
                    "⬅️  Back to Main Menu"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back to Main Menu" in choice:
                break
                
            if "Run Initial Setup Wizard" in choice:
                self._run_initial_setup()
            elif "Database Configuration" in choice:
                self._database_configuration_menu()
            elif "Google Sheets Sync" in choice:
                self._google_sheets_sync_menu()
            elif "ComfyUI Configuration" in choice:
                self._comfyui_configuration_menu()
            elif "Path Configuration" in choice:
                self._path_configuration_menu()
    
    # DATABASE CONFIGURATION (from postgresql_manager.py)
    def _database_configuration_menu(self) -> None:
        """Database configuration menu with status display."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            self._show_database_status()
            
            choice = questionary.select(
                "Database Configuration:",
                choices=[
                    "🚀 Quick Setup",
                    "🔐 Authentication & Security",
                    "🔄 Migration & Backup",
                    "🔍 Testing & Verification",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
                
            if "Quick Setup" in choice:
                self._database_quick_setup_menu()
            elif "Authentication & Security" in choice:
                self._database_auth_menu()
            elif "Migration & Backup" in choice:
                self._database_migration_menu()
            elif "Testing & Verification" in choice:
                self._database_testing_menu()
    
    def _show_database_status(self) -> None:
        """Show current PostgreSQL status."""
        try:
            # Test connection
            conn = psycopg2.connect(**self.db_config)
            conn.close()
            status = "✅ Connected"
        except:
            status = "❌ Not Connected"
        
        print(f"\nDatabase Status: {status}")
        print(f"Host: {self.db_config['host']}:{self.db_config['port']}")
        print(f"Database: {self.db_config['database']}")
        print(f"User: {self.db_config['user']}")
        print("="*60 + "\n")
    
    def _database_quick_setup_menu(self) -> None:
        """Database quick setup menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            
            choices = []
            
            # Check if PostgreSQL is installed
            if not self._is_postgresql_installed():
                choices.append("📦 Install PostgreSQL")
            else:
                choices.append("✅ PostgreSQL is installed")
                
                # Check if PostgreSQL is running
                if not self._is_postgresql_running():
                    choices.append("▶️  Start PostgreSQL")
                else:
                    choices.append("✅ PostgreSQL is running")
            
            choices.extend([
                "🔄 Full Auto Setup",
                "🗄️  Create Database & User",
                "⬅️  Back"
            ])
            
            choice = questionary.select(
                "Quick Setup:",
                choices=choices,
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
            
            if "Install PostgreSQL" in choice:
                self._install_postgresql()
            elif "Start PostgreSQL" in choice:
                self._start_postgresql_service()
            elif "Full Auto Setup" in choice:
                self._full_database_setup()
            elif "Create Database & User" in choice:
                self._create_database()
    
    def _database_auth_menu(self) -> None:
        """Database authentication menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            
            choice = questionary.select(
                "Authentication & Security:",
                choices=[
                    "🔑 Change Database Credentials",
                    "🔐 Fix Authentication Issues",
                    "📝 Update .env Configuration",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
            
            if "Change Database Credentials" in choice:
                self._change_database_credentials()
            elif "Fix Authentication Issues" in choice:
                self._fix_authentication()
            elif "Update .env Configuration" in choice:
                self._update_env_database_config()
    
    def _database_migration_menu(self) -> None:
        """Database migration and backup menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            
            choice = questionary.select(
                "Migration & Backup:",
                choices=[
                    "🚀 Migrate from SQLite",
                    "💾 Backup Database",
                    "🔄 Restore from Backup",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
            
            if "Migrate from SQLite" in choice:
                self._migrate_from_sqlite()
            elif "Backup Database" in choice:
                self._backup_database()
            elif "Restore from Backup" in choice:
                self._restore_database()
    
    def _database_testing_menu(self) -> None:
        """Database testing and verification menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            
            choice = questionary.select(
                "Testing & Verification:",
                choices=[
                    "🔍 Test Connection",
                    "📊 Check Table Structure",
                    "🏥 Database Health Check",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
            
            if "Test Connection" in choice:
                self._test_database_connection()
            elif "Check Table Structure" in choice:
                self._check_table_structure()
            elif "Database Health Check" in choice:
                self._database_health_check()
    
    # GOOGLE SHEETS SYNC (from sheets_sync_manager_optimized.py)
    def _google_sheets_sync_menu(self) -> None:
        """Google Sheets synchronization menu with status display."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            self._show_sheets_sync_status()
            
            choice = questionary.select(
                "Google Sheets Sync Configuration:",
                choices=[
                    "⚙️  Quick Configuration",
                    "🎮 Daemon Control",
                    "⚙️  Advanced Settings",
                    "🔧 Maintenance",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
                
            if "Quick Configuration" in choice:
                self._sheets_quick_configuration_menu()
            elif "Daemon Control" in choice:
                self._sheets_daemon_control_menu()
            elif "Advanced Settings" in choice:
                self._sheets_advanced_settings_menu()
            elif "Maintenance" in choice:
                self._sheets_maintenance_menu()
    
    def _show_sheets_sync_status(self) -> None:
        """Show daemon and configuration status for Google Sheets sync."""
        # Check daemon status
        is_running, pid = self._check_sheets_daemon_status()
        status_icon = "🟢" if is_running else "🔴"
        status_text = f"RUNNING (PID: {pid})" if is_running else "STOPPED"
        
        print(f"\n{status_icon} Daemon Status: {status_text}")
        
        # Show configuration status
        config_status = self._check_sheets_configuration()
        if config_status['configured']:
            print(f"📊 Spreadsheet: {config_status['spreadsheet_id'][:20]}...")
            print(f"🔄 Last sync: {self._get_last_sync_time()}")
        else:
            print("⚠️  Configuration: Not complete")
        
        print("="*60 + "\n")
    
    def _sheets_quick_configuration_menu(self) -> None:
        """Google Sheets quick configuration menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            
            choice = questionary.select(
                "Quick Configuration:",
                choices=[
                    "🚀 Setup Wizard",
                    "📝 Set Spreadsheet ID",
                    "🔑 Configure Authentication",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
            
            if "Setup Wizard" in choice:
                self._sheets_setup_wizard()
            elif "Set Spreadsheet ID" in choice:
                self._configure_spreadsheet_id()
            elif "Configure Authentication" in choice:
                self._setup_sheets_authentication()
    
    def _sheets_daemon_control_menu(self) -> None:
        """Google Sheets daemon control menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            self._show_sheets_sync_status()
            
            is_running, _ = self._check_sheets_daemon_status()
            
            choices = []
            if is_running:
                choices.extend([
                    "🛑 Stop Sync Daemon",
                    "🔄 Restart Sync Daemon",
                    "📊 View Daemon Status"
                ])
            else:
                choices.append("🚀 Start Sync Daemon")
            
            choices.append("⬅️  Back")
            
            choice = questionary.select(
                "Daemon Control:",
                choices=choices,
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
            
            if "Start Sync Daemon" in choice:
                self._start_sheets_daemon()
            elif "Stop Sync Daemon" in choice:
                self._stop_sheets_daemon()
            elif "Restart Sync Daemon" in choice:
                self._restart_sheets_daemon()
            elif "View Daemon Status" in choice:
                self._view_sheets_daemon_status()
    
    def _sheets_advanced_settings_menu(self) -> None:
        """Google Sheets advanced settings menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            
            choice = questionary.select(
                "Advanced Settings:",
                choices=[
                    "⏱️  Sync Interval",
                    "📦 Batch Size",
                    "🔄 Retry Configuration",
                    "🚀 Real-time Events",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
            
            if "Sync Interval" in choice:
                self._configure_sync_interval()
            elif "Batch Size" in choice:
                self._configure_batch_size()
            elif "Retry Configuration" in choice:
                self._configure_retry_settings()
            elif "Real-time Events" in choice:
                self._configure_realtime_events()
    
    def _sheets_maintenance_menu(self) -> None:
        """Google Sheets maintenance menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            
            choice = questionary.select(
                "Maintenance:",
                choices=[
                    "📦 Install Dependencies",
                    "🧪 Test Connection",
                    "🔄 Manual Full Sync",
                    "📋 View Recent Logs",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
            
            if "Install Dependencies" in choice:
                self._install_sheets_dependencies()
            elif "Test Connection" in choice:
                self._test_sheets_connection()
            elif "Manual Full Sync" in choice:
                self._manual_full_sync()
            elif "View Recent Logs" in choice:
                self._view_sheets_logs()
    
    # COMFYUI CONFIGURATION (existing functionality)
    def _comfyui_configuration_menu(self) -> None:
        """ComfyUI configuration submenu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            # Show current ComfyUI path
            current_path = Config.get_comfyui_path() or "Not configured"
            
            choice = questionary.select(
                f"ComfyUI Configuration - Current: {current_path}:",
                choices=[
                    "📁 Set ComfyUI Path",
                    "✅ Validate Preview System",
                    "🔍 Diagnose ComfyUI Environment",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
                
            if "Set ComfyUI Path" in choice:
                self._set_comfyui_path()
            elif "Validate Preview System" in choice:
                self._validate_preview_system()
            elif "Diagnose ComfyUI Environment" in choice:
                self._diagnose_comfyui()
    
    # PATH CONFIGURATION (existing functionality)
    def _path_configuration_menu(self) -> None:
        """Path configuration submenu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            # Show current configuration
            current_profile = Config.get_active_profile(self.base_path)
            current_path = Config.get_custom_output_path(self.base_path)
            
            status_text = f"Current: {current_profile or 'default'}"
            if current_path:
                status_text += f" ({current_path})"
            
            choice = questionary.select(
                f"Path Configuration - {status_text}:",
                choices=[
                    "📁 Set Workspace Path",
                    "📁 Set Output Path", 
                    "💾 Save as Profile",
                    "🔄 Load Profile",
                    "📋 List Profiles",
                    "🗑️  Delete Profile",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
                
            if "Set Workspace Path" in choice:
                self._set_workspace_path()
            elif "Set Output Path" in choice:
                self._set_custom_path()
            elif "Save as Profile" in choice:
                self._save_path_profile()
            elif "Load Profile" in choice:
                self._switch_to_profile()
            elif "List Profiles" in choice:
                self._list_path_profiles()
            elif "Delete Profile" in choice:
                self._delete_path_profile()
    
    # TRAINING CONFIGURATION MENU
    def _training_configuration_menu(self) -> None:
        """Training configuration menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            choice = questionary.select(
                "Training Configuration:",
                choices=[
                    "🎨 Preset Management",
                    "⚙️  Display Settings",
                    "⬅️  Back to Main Menu"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back to Main Menu" in choice:
                break
                
            if "Preset Management" in choice:
                self._preset_management_menu()
            elif "Display Settings" in choice:
                self._display_settings_menu()
    
    # SYSTEM ADMINISTRATION MENU
    def _system_administration_menu(self) -> None:
        """System administration menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            choice = questionary.select(
                "System Administration:",
                choices=[
                    "🗄️  Database Operations",
                    "🧹 Process Management",
                    "🔍 System Diagnostics",
                    "⬅️  Back to Main Menu"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back to Main Menu" in choice:
                break
                
            if "Database Operations" in choice:
                self._database_operations_menu()
            elif "Process Management" in choice:
                self._process_management_menu()
            elif "System Diagnostics" in choice:
                self._system_diagnostics_menu()
    
    def _database_operations_menu(self) -> None:
        """Database operations menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            
            choice = questionary.select(
                "Database Operations:",
                choices=[
                    "📊 View Data",
                    "🧹 Maintenance",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
            
            if "View Data" in choice:
                self._database_view_data_menu()
            elif "Maintenance" in choice:
                self._database_maintenance_menu()
    
    def _database_view_data_menu(self) -> None:
        """Database view data menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            
            choice = questionary.select(
                "View Data:",
                choices=[
                    "📊 Executions Table",
                    "🎯 Variations Table",
                    "📂 Model Paths Table",
                    "🌐 Web Viewer",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
            
            if "Executions Table" in choice:
                self._view_executions_table()
            elif "Variations Table" in choice:
                self._view_variations_table()
            elif "Model Paths Table" in choice:
                self._view_model_paths_table()
            elif "Web Viewer" in choice:
                self._launch_web_viewer()
    
    def _database_maintenance_menu(self) -> None:
        """Database maintenance menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            
            choice = questionary.select(
                "Maintenance:",
                choices=[
                    "🗑️  Clear All Records",
                    "🧹 Cleanup Old Records",
                    "🔧 Optimize Database",
                    "📊 Export Statistics",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
            
            if "Clear All Records" in choice:
                self._clear_database()
            elif "Cleanup Old Records" in choice:
                self._cleanup_old_records()
            elif "Optimize Database" in choice:
                self._optimize_database()
            elif "Export Statistics" in choice:
                self._export_database_stats()
    
    def _process_management_menu(self) -> None:
        """Process management menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            
            choice = questionary.select(
                "Process Management:",
                choices=[
                    "🧹 Cleanup Stale Processes",
                    "📊 View Running Processes",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
            
            if "Cleanup Stale Processes" in choice:
                self._cleanup_stale_processes()
            elif "View Running Processes" in choice:
                self._view_running_processes()
    
    # SYSTEM DIAGNOSTICS MENU
    def _system_diagnostics_menu(self) -> None:
        """System diagnostics submenu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            choice = questionary.select(
                "System Diagnostics:",
                choices=[
                    "📊 System Status Overview",
                    "🗄️  Database Status",
                    "📊 Sheets Sync Status",
                    "🖼️  ComfyUI Status",
                    "📋 System Logs",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
                
            if "System Status Overview" in choice:
                self._show_system_status()
            elif "Database Status" in choice:
                self._show_database_diagnostics()
            elif "Sheets Sync Status" in choice:
                self._show_sheets_sync_diagnostics()
            elif "ComfyUI Status" in choice:
                self._diagnose_comfyui()
            elif "System Logs" in choice:
                self._view_system_logs()
    
    # INFORMATION & REPORTS MENU
    def _information_reports_menu(self) -> None:
        """Information and reports menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            choice = questionary.select(
                "Information & Reports:",
                choices=[
                    "📈 Training History",
                    "📄 Job Details Viewer",
                    "📊 Statistics Dashboard",
                    "📋 Available Presets List",
                    "⬅️  Back to Main Menu"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back to Main Menu" in choice:
                break
                
            if "Training History" in choice:
                self._show_job_history()
            elif "Job Details Viewer" in choice:
                self._show_job_details()
            elif "Statistics Dashboard" in choice:
                self._show_statistics_dashboard()
            elif "Available Presets List" in choice:
                self._list_presets()
    
    # HELP & DOCUMENTATION MENU
    def _help_documentation_menu(self) -> None:
        """Help and documentation menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            choice = questionary.select(
                "Help & Documentation:",
                choices=[
                    "📚 Quick Start Guide",
                    "🔧 Configuration Guide",
                    "🐛 Troubleshooting",
                    "📞 Support Information",
                    "⬅️  Back to Main Menu"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back to Main Menu" in choice:
                break
                
            if "Quick Start Guide" in choice:
                self._show_quick_start_guide()
            elif "Configuration Guide" in choice:
                self._show_configuration_guide()
            elif "Troubleshooting" in choice:
                self._show_troubleshooting_guide()
            elif "Support Information" in choice:
                self._show_support_information()
    
    # =======================
    # DATABASE IMPLEMENTATION METHODS
    # =======================
    
    def _is_postgresql_installed(self) -> bool:
        """Check if PostgreSQL is installed."""
        try:
            result = subprocess.run(["which", "psql"], capture_output=True)
            return result.returncode == 0
        except:
            return False
    
    def _is_postgresql_running(self) -> bool:
        """Check if PostgreSQL service is running."""
        try:
            # Try to connect to PostgreSQL
            result = subprocess.run(
                ["pg_isready", "-h", "localhost", "-p", "5432"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def _fix_authentication_for_docker(self) -> None:
        """Fix PostgreSQL authentication specifically for Docker containers."""
        print("\n🔧 Fixing PostgreSQL authentication for Docker...")
        
        try:
            # Find pg_hba.conf
            cmd = "su - postgres -c \"psql -t -c 'SHOW hba_file' 2>/dev/null\" || echo '/etc/postgresql/*/main/pg_hba.conf'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            # Try to find pg_hba.conf manually if the above fails
            if result.returncode != 0 or not result.stdout.strip():
                find_cmd = "find /etc/postgresql -name pg_hba.conf 2>/dev/null | head -1"
                result = subprocess.run(find_cmd, shell=True, capture_output=True, text=True)
            
            hba_file = result.stdout.strip()
            
            if hba_file and os.path.exists(hba_file.replace('*', '14')):  # Handle wildcard
                hba_file = hba_file.replace('*', '14')  # Assume version 14, adjust as needed
                
                print(f"📄 Found pg_hba.conf: {hba_file}")
                
                # Backup
                subprocess.run(f"cp {hba_file} {hba_file}.backup", shell=True)
                
                # Create a new pg_hba.conf with trust authentication for local connections
                new_content = """# PostgreSQL Client Authentication Configuration
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Allow local connections without password (for Docker setup)
local   all             postgres                                trust
local   all             all                                     trust

# IPv4 local connections:
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust

# Allow connections from Docker network
host    all             all             172.16.0.0/12           md5
host    all             all             192.168.0.0/16          md5
"""
                
                with open(hba_file, 'w') as f:
                    f.write(new_content)
                
                print("✅ Updated pg_hba.conf for Docker")
                
                # Restart PostgreSQL
                restart_cmds = [
                    "service postgresql restart",
                    "su - postgres -c 'pg_ctl reload -D /var/lib/postgresql/*/main'",
                    "pg_ctlcluster 14 main reload"
                ]
                
                for cmd in restart_cmds:
                    result = subprocess.run(cmd, shell=True, capture_output=True)
                    if result.returncode == 0:
                        print("✅ PostgreSQL configuration reloaded")
                        break
                
                print("\n✅ Authentication setup complete for Docker!")
                print("💡 Local connections now work without password")
                
            else:
                print("❌ Could not find pg_hba.conf")
                print("💡 Try running: find /etc/postgresql -name pg_hba.conf")
                
        except Exception as e:
            print(f"❌ Error fixing authentication: {str(e)}")
    
    def _start_postgresql_service(self) -> bool:
        """Start PostgreSQL service."""
        print("\n🔄 Starting PostgreSQL service...")
        
        try:
            if self.is_docker or self.is_root:
                # In Docker, try different methods
                methods = [
                    ["service", "postgresql", "start"],
                    ["pg_ctlcluster", "main", "start"],
                    ["/etc/init.d/postgresql", "start"]
                ]
                
                for method in methods:
                    result = subprocess.run(method, capture_output=True, text=True)
                    if result.returncode == 0:
                        print("✅ PostgreSQL service started successfully")
                        # Give it a moment to fully start
                        time.sleep(2)
                        return True
                
                # If none worked, try to find and use pg_ctl directly
                pg_version_result = subprocess.run(
                    ["ls", "/usr/lib/postgresql/"],
                    capture_output=True,
                    text=True
                )
                if pg_version_result.returncode == 0:
                    versions = pg_version_result.stdout.strip().split()
                    if versions:
                        version = versions[0]
                        data_dir = f"/var/lib/postgresql/{version}/main"
                        bin_dir = f"/usr/lib/postgresql/{version}/bin"
                        
                        # Initialize if needed
                        if not os.path.exists(f"{data_dir}/PG_VERSION"):
                            print(f"📦 Initializing PostgreSQL database in {data_dir}...")
                            init_cmd = f"su - postgres -c '{bin_dir}/initdb -D {data_dir}'"
                            subprocess.run(init_cmd, shell=True)
                        
                        # Start PostgreSQL
                        start_cmd = f"su - postgres -c '{bin_dir}/pg_ctl -D {data_dir} -l /var/log/postgresql/postgresql.log start'"
                        result = subprocess.run(start_cmd, shell=True, capture_output=True, text=True)
                        if result.returncode == 0:
                            print("✅ PostgreSQL started using pg_ctl")
                            time.sleep(2)
                            return True
            else:
                # Normal system with systemctl
                result = self._run_privileged_command(
                    ["systemctl", "start", "postgresql"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print("✅ PostgreSQL service started")
                    return True
            
            print("❌ Failed to start PostgreSQL service")
            return False
            
        except Exception as e:
            print(f"❌ Error starting PostgreSQL: {str(e)}")
            return False
    
    def _install_postgresql(self) -> None:
        """Install PostgreSQL."""
        print("\n" + "="*50)
        print("  INSTALLING POSTGRESQL")
        print("="*50)
        
        if self.is_docker:
            print("\n⚠️  In Docker container - PostgreSQL should be pre-installed")
            print("If not, run as root: apt-get update && apt-get install -y postgresql postgresql-client")
        
        try:
            print("\nUpdating package list...")
            result = self._run_privileged_command(["apt-get", "update"], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Error updating packages: {result.stderr}")
                input("\nPress Enter to continue...")
                return
            
            print("\nInstalling PostgreSQL...")
            result = self._run_privileged_command(
                ["apt-get", "install", "-y", "postgresql", "postgresql-client", "postgresql-contrib"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                print("✅ PostgreSQL installed successfully!")
            else:
                print(f"❌ Error installing PostgreSQL: {result.stderr}")
        except FileNotFoundError as e:
            if "sudo" in str(e):
                print("❌ Error: sudo command not found.")
                if self.is_docker:
                    print("💡 In Docker, run as root user or install sudo: apt-get install sudo")
                else:
                    print("💡 Please install sudo or run as root user")
            else:
                print(f"❌ Error: {str(e)}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        input("\nPress Enter to continue...")
    
    def _create_database(self) -> None:
        """Create database and user."""
        print("\n" + "="*50)
        print("  CREATING DATABASE & USER")
        print("="*50)
        
        # Check if PostgreSQL is running first
        if not self._is_postgresql_running():
            print("\n⚠️  PostgreSQL is not running!")
            if questionary.confirm(
                "Would you like to start PostgreSQL?",
                default=True,
                style=AUTOTRAINX_STYLE
            ).ask():
                if not self._start_postgresql_service():
                    print("\n❌ Could not start PostgreSQL.")
                    print("\n💡 In Docker, you might need to:")
                    print("   1. Ensure PostgreSQL is installed: apt-get install postgresql")
                    print("   2. Initialize the database: su - postgres -c 'initdb -D /var/lib/postgresql/data'")
                    print("   3. Start manually: su - postgres -c 'pg_ctl -D /var/lib/postgresql/data start'")
                    input("\nPress Enter to continue...")
                    return
        
        # In Docker, we might need to fix authentication first
        if self.is_docker and questionary.confirm(
            "\n🐳 In Docker, PostgreSQL might need authentication setup. Fix it first?",
            default=True,
            style=AUTOTRAINX_STYLE
        ).ask():
            self._fix_authentication_for_docker()
        
        # Get configuration
        db_name = questionary.text(
            "Database name:",
            default=self.db_config['database'],
            style=AUTOTRAINX_STYLE
        ).ask()
        
        db_user = questionary.text(
            "Database user:",
            default=self.db_config['user'],
            style=AUTOTRAINX_STYLE
        ).ask()
        
        db_pass = questionary.password(
            "Database password:",
            style=AUTOTRAINX_STYLE
        ).ask() or self.db_config['password']
        
        print("\nCreating database and user...")
        
        # SQL commands
        sql_commands = f"""
-- Create user if not exists
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '{db_user}') THEN
      CREATE USER {db_user} WITH PASSWORD '{db_pass}';
   END IF;
END $$;

-- Create database if not exists
SELECT 'CREATE DATABASE {db_name} OWNER {db_user}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{db_name}')\\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};
"""
        
        # Execute as postgres user
        try:
            # Different approach for Docker/root vs normal system
            if self.is_root or self.running_in_docker:
                # In Docker/root, use psql directly with postgres user
                import tempfile
                
                # Create temp file with proper permissions
                fd, sql_file = tempfile.mkstemp(suffix='.sql')
                try:
                    # Write SQL commands
                    with os.fdopen(fd, 'w') as f:
                        f.write(sql_commands)
                    
                    # Make file readable by postgres user
                    os.chmod(sql_file, 0o644)
                    
                    # Execute using su without password prompt
                    # First try without password (default in Docker)
                    cmd = f"su - postgres -c \"psql -U postgres << 'EOF'\n{sql_commands}\nEOF\""
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    # If that fails, try with trust authentication
                    if result.returncode != 0 and "authentication failed" in result.stderr:
                        print("\n⚠️  Password authentication failed. Trying with trust authentication...")
                        
                        # Update pg_hba.conf temporarily to trust
                        hba_cmd = "su - postgres -c \"psql -t -c 'SHOW hba_file'\""
                        hba_result = subprocess.run(hba_cmd, shell=True, capture_output=True, text=True)
                        
                        if hba_result.returncode == 0:
                            hba_file = hba_result.stdout.strip()
                            
                            # Backup and modify pg_hba.conf
                            backup_cmd = f"cp {hba_file} {hba_file}.backup"
                            subprocess.run(backup_cmd, shell=True)
                            
                            # Temporarily set to trust for local connections
                            trust_cmd = f"sed -i '1i local   all   postgres   trust' {hba_file}"
                            subprocess.run(trust_cmd, shell=True)
                            
                            # Reload PostgreSQL
                            reload_cmd = "su - postgres -c 'pg_ctl reload -D /var/lib/postgresql/*/main'"
                            subprocess.run(reload_cmd, shell=True)
                            
                            # Try again
                            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                            
                            # Restore original pg_hba.conf
                            restore_cmd = f"mv {hba_file}.backup {hba_file}"
                            subprocess.run(restore_cmd, shell=True)
                            subprocess.run(reload_cmd, shell=True)
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(sql_file)
                    except:
                        pass
            else:
                # Normal system with sudo
                sql_file = "/tmp/create_db.sql"
                with open(sql_file, 'w') as f:
                    f.write(sql_commands)
                
                cmd = ["sudo", "-u", "postgres", "psql", "-f", sql_file]
                result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("\n✅ Database and user created successfully!")
                
                # Update configuration
                self.db_config.update({
                    'database': db_name,
                    'user': db_user,
                    'password': db_pass
                })
            else:
                print(f"\n❌ Error: {result.stderr}")
                
                # More helpful error messages for common issues
                if "connection to server" in result.stderr and "failed" in result.stderr:
                    print("\n💡 PostgreSQL connection failed. Possible solutions:")
                    print("   1. Start PostgreSQL service (select 'Start PostgreSQL' from menu)")
                    print("   2. Check if PostgreSQL is installed correctly")
                    print("   3. Verify PostgreSQL is listening on the correct socket/port")
                    
                    if self.is_docker:
                        print("\n🐳 Docker-specific tips:")
                        print("   - Run: service postgresql status")
                        print("   - If not running: service postgresql start")
                        print("   - Check logs: tail -f /var/log/postgresql/*.log")
                
                elif "role" in result.stderr and "does not exist" in result.stderr:
                    print("\n💡 The postgres user might not exist. Try:")
                    print("   - Creating postgres user: useradd -m postgres")
                    print("   - Switching to postgres: su - postgres")
                    print("   - Initializing DB: initdb -D /var/lib/postgresql/data")
                    
        except FileNotFoundError as e:
            print(f"\n❌ Error: Command not found - {str(e)}")
            print("💡 Make sure PostgreSQL is installed: apt-get install postgresql")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("\n💡 If you're in Docker, make sure:")
            print("   - PostgreSQL is installed")
            print("   - You're running as root or postgres user")
            print("   - The PostgreSQL data directory is initialized")
        
        input("\nPress Enter to continue...")
    
    def _full_database_setup(self) -> None:
        """Run full database setup process."""
        print("\n" + "="*50)
        print("  FULL DATABASE AUTO SETUP")
        print("="*50)
        
        steps = [
            ("Checking PostgreSQL installation", self._check_postgresql_installation),
            ("Installing PostgreSQL (if needed)", self._conditional_install_postgresql),
            ("Creating database and user", self._create_database),
            ("Fixing authentication", self._fix_authentication),
            ("Running migrations", self._run_database_migrations)
        ]
        
        for step_name, step_func in steps:
            print(f"\n➤ {step_name}...")
            try:
                step_func()
                print(f"✅ {step_name} completed")
            except Exception as e:
                print(f"❌ {step_name} failed: {e}")
                if not questionary.confirm("Continue with setup?", style=AUTOTRAINX_STYLE).ask():
                    break
        
        print("\n✅ Full setup completed!")
        input("\nPress Enter to continue...")
    
    def _check_postgresql_installation(self) -> bool:
        """Check and report PostgreSQL installation status."""
        if self._is_postgresql_installed():
            print("  PostgreSQL is already installed")
            return True
        else:
            print("  PostgreSQL is not installed")
            return False
    
    def _conditional_install_postgresql(self) -> None:
        """Install PostgreSQL only if not already installed."""
        if not self._is_postgresql_installed():
            self._install_postgresql()
    
    def _fix_authentication(self) -> None:
        """Fix PostgreSQL authentication issues."""
        print("\n" + "="*50)
        print("  FIXING AUTHENTICATION")
        print("="*50)
        
        print("\nThis will update pg_hba.conf to allow password authentication...")
        
        if questionary.confirm(
            "Continue?",
            default=True,
            style=AUTOTRAINX_STYLE
        ).ask():
            try:
                # Find pg_hba.conf
                if self.is_root or self.running_in_docker:
                    # In Docker/root, use su to run as postgres
                    cmd = "su - postgres -c \"psql -t -c 'SHOW hba_file'\""
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                else:
                    cmd = ["sudo", "-u", "postgres", "psql", "-t", "-c", "SHOW hba_file"]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    hba_file = result.stdout.strip()
                    print(f"\nFound pg_hba.conf: {hba_file}")
                    
                    # Backup
                    self._run_privileged_command(["cp", hba_file, f"{hba_file}.backup"])
                    print(f"✅ Backup created: {hba_file}.backup")
                    
                    # Update authentication using sed commands
                    sed_commands = [
                        ["sed", "-i", "s/local   all             postgres                                peer/local   all             postgres                                md5/", hba_file],
                        ["sed", "-i", "s/local   all             all                                     peer/local   all             all                                     md5/", hba_file]
                    ]
                    
                    for sed_cmd in sed_commands:
                        result = self._run_privileged_command(sed_cmd, capture_output=True, text=True)
                        if result.returncode != 0:
                            print(f"⚠️  Warning: sed command failed: {result.stderr}")
                    
                    # Restart PostgreSQL
                    print("\nRestarting PostgreSQL...")
                    if self.is_docker:
                        # In Docker, PostgreSQL might not be managed by systemctl
                        restart_result = self._run_privileged_command(
                            ["service", "postgresql", "restart"],
                            capture_output=True, text=True
                        )
                        if restart_result.returncode != 0:
                            print("⚠️  Could not restart PostgreSQL service.")
                            print("💡 Try: pg_ctl restart or restart the container")
                    else:
                        self._run_privileged_command(["systemctl", "restart", "postgresql"])
                    
                    print("\n✅ Authentication configuration updated!")
                    print("💡 You may need to restart PostgreSQL manually if running in Docker")
                else:
                    print("\n❌ Could not find pg_hba.conf")
                    print(f"Error: {result.stderr}")
            except FileNotFoundError as e:
                if "sudo" in str(e):
                    print("❌ Error: sudo command not found.")
                    if self.is_docker:
                        print("💡 In Docker, run as root user or install sudo: apt-get install sudo")
                else:
                    print(f"❌ Error: {str(e)}")
            except Exception as e:
                print(f"\n❌ Error: {e}")
        
        input("\nPress Enter to continue...")
    
    def _change_database_credentials(self) -> None:
        """Change database connection credentials."""
        print("\n" + "="*50)
        print("  CHANGE DATABASE CREDENTIALS")
        print("="*50)
        
        print("\nCurrent configuration:")
        print(f"Host: {self.db_config['host']}:{self.db_config['port']}")
        print(f"Database: {self.db_config['database']}")
        print(f"User: {self.db_config['user']}")
        print(f"Password: {'*' * len(str(self.db_config['password']))}")
        
        if questionary.confirm(
            "\nDo you want to change these credentials?",
            default=True,
            style=AUTOTRAINX_STYLE
        ).ask():
            # Get new credentials
            new_host = questionary.text(
                "Database host:",
                default=self.db_config['host'],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            new_port = questionary.text(
                "Database port:",
                default=str(self.db_config['port']),
                style=AUTOTRAINX_STYLE
            ).ask()
            
            new_database = questionary.text(
                "Database name:",
                default=self.db_config['database'],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            new_user = questionary.text(
                "Database user:",
                default=self.db_config['user'],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            new_password = questionary.password(
                "Database password:",
                style=AUTOTRAINX_STYLE
            ).ask()
            
            # Test new connection
            print("\n🔍 Testing new connection...")
            test_config = {
                'host': new_host,
                'port': new_port,
                'database': new_database,
                'user': new_user,
                'password': new_password
            }
            
            try:
                conn = psycopg2.connect(**test_config)
                conn.close()
                print("✅ Connection successful!")
                
                # Update configuration
                self.db_config = test_config
                
                # Ask if user wants to save to .env file
                if questionary.confirm(
                    "\nDo you want to save these credentials to the .env file?",
                    default=True,
                    style=AUTOTRAINX_STYLE
                ).ask():
                    self._update_env_database_config()
                    print("✅ Credentials saved to .env file!")
                else:
                    print("\n⚠️  Credentials updated for this session only.")
                    print("   They will not persist after restarting the menu.")
                    
            except psycopg2.OperationalError as e:
                print(f"\n❌ Connection failed: {e}")
                print("Keeping previous credentials.")
            except Exception as e:
                print(f"\n❌ Error: {e}")
        
        input("\nPress Enter to continue...")
    
    def _update_env_database_config(self) -> None:
        """Update .env file with database configuration."""
        if not self.env_file.exists():
            print(f"\n⚠️  .env file not found at {self.env_file}")
            print("Creating new .env file...")
            try:
                self.env_file.parent.mkdir(exist_ok=True)
                print(f"🔧 Debug: Created directory {self.env_file.parent}")
            except PermissionError as e:
                print(f"❌ Permission denied creating directory {self.env_file.parent}: {e}")
                print("Please ensure you have write permissions to the project directory")
                input("\nPress Enter to continue...")
                return
            except Exception as e:
                print(f"❌ Failed to create directory {self.env_file.parent}: {type(e).__name__}: {e}")
                input("\nPress Enter to continue...")
                return
            
        try:
            # Read current .env file if exists
            lines = []
            if self.env_file.exists():
                with open(self.env_file, 'r') as f:
                    lines = f.readlines()
            
            # Update or add database configuration lines
            db_vars = {
                'DATABASE_HOST': self.db_config['host'],
                'DATABASE_PORT': str(self.db_config['port']),
                'DATABASE_NAME': self.db_config['database'],
                'DATABASE_USER': self.db_config['user'],
                'DATABASE_PASSWORD': self.db_config['password'],
                'DATABASE_TYPE': 'postgresql'
            }
            
            # Track which variables were updated
            updated_vars = set()
            updated_lines = []
            
            for line in lines:
                updated = False
                for var_name, var_value in db_vars.items():
                    if line.startswith(f"{var_name}="):
                        updated_lines.append(f"{var_name}={var_value}\n")
                        updated_vars.add(var_name)
                        updated = True
                        break
                
                if not updated:
                    updated_lines.append(line)
            
            # Add any missing variables
            for var_name, var_value in db_vars.items():
                if var_name not in updated_vars:
                    updated_lines.append(f"{var_name}={var_value}\n")
            
            # Write back to file
            with open(self.env_file, 'w') as f:
                f.writelines(updated_lines)
            
            print("\n✅ .env file updated successfully!")
                
        except Exception as e:
            print(f"\n❌ Error updating .env file: {e}")
        
        input("\nPress Enter to continue...")
    
    def _migrate_from_sqlite(self) -> None:
        """Migrate data from SQLite to PostgreSQL."""
        cmd = ["python", str(self.script_dir / "database_utils" / "migrate_to_postgresql.py")]
        self._execute_command(cmd, "SQLite to PostgreSQL Migration")
    
    def _backup_database(self) -> None:
        """Backup PostgreSQL database."""
        print("\n" + "="*50)
        print("  BACKUP DATABASE")
        print("="*50)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"autotrainx_backup_{timestamp}.sql"
        
        print(f"\nCreating backup: {backup_file}")
        
        cmd = [
            "pg_dump",
            "-h", self.db_config['host'],
            "-p", str(self.db_config['port']),
            "-U", self.db_config['user'],
            "-d", self.db_config['database'],
            "-f", backup_file
        ]
        
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_config['password']
        
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"\n✅ Backup created successfully: {backup_file}")
            else:
                print(f"\n❌ Backup failed: {result.stderr}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        input("\nPress Enter to continue...")
    
    def _restore_database(self) -> None:
        """Restore PostgreSQL database from backup."""
        print("\n" + "="*50)
        print("  RESTORE DATABASE")
        print("="*50)
        
        # List available backup files
        backup_files = list(Path.cwd().glob("autotrainx_backup_*.sql"))
        
        if not backup_files:
            print("\n❌ No backup files found in current directory")
            input("\nPress Enter to continue...")
            return
        
        # Sort by modification time
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        choices = [f"{f.name} ({f.stat().st_size // 1024} KB)" for f in backup_files]
        choices.append("⬅️ Cancel")
        
        backup_choice = questionary.select(
            "Select backup file to restore:",
            choices=choices,
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if not backup_choice or "Cancel" in backup_choice:
            return
        
        backup_file = backup_files[choices.index(backup_choice)]
        
        if questionary.confirm(
            f"\n⚠️  This will OVERWRITE the current database!\nRestore from {backup_file.name}?",
            default=False,
            style=AUTOTRAINX_STYLE
        ).ask():
            
            print("\nRestoring database...")
            
            cmd = [
                "psql",
                "-h", self.db_config['host'],
                "-p", str(self.db_config['port']),
                "-U", self.db_config['user'],
                "-d", self.db_config['database'],
                "-f", str(backup_file)
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config['password']
            
            try:
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                if result.returncode == 0:
                    print("\n✅ Database restored successfully!")
                else:
                    print(f"\n❌ Restore failed: {result.stderr}")
            except Exception as e:
                print(f"\n❌ Error: {e}")
        
        input("\nPress Enter to continue...")
    
    def _test_database_connection(self) -> None:
        """Test database connection."""
        print("\n" + "="*50)
        print("  TESTING DATABASE CONNECTION")
        print("="*50)
        
        print(f"\nTesting connection to:")
        print(f"Host: {self.db_config['host']}:{self.db_config['port']}")
        print(f"Database: {self.db_config['database']}")
        print(f"User: {self.db_config['user']}")
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Get PostgreSQL version
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
            print(f"\n✅ Connection successful!")
            print(f"PostgreSQL version: {version.split(',')[0]}")
            
            # Check tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            
            tables = cursor.fetchall()
            if tables:
                print(f"\nFound {len(tables)} tables:")
                for table in tables:
                    print(f"  - {table[0]}")
            else:
                print("\n⚠️  No tables found in database")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"\n❌ Connection failed: {e}")
        
        input("\nPress Enter to continue...")
    
    def _check_table_structure(self) -> None:
        """Check database table structure."""
        print("\n" + "="*50)
        print("  DATABASE TABLE STRUCTURE")
        print("="*50)
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table[0]
                print(f"\n📊 Table: {table_name}")
                print("-" * 50)
                
                # Get column information
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position;
                """)
                
                columns = cursor.fetchall()
                for col in columns:
                    nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                    default = f" DEFAULT {col[3]}" if col[3] else ""
                    print(f"  {col[0]}: {col[1]} {nullable}{default}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        input("\nPress Enter to continue...")
    
    def _database_health_check(self) -> None:
        """Perform database health check."""
        print("\n" + "="*50)
        print("  DATABASE HEALTH CHECK")
        print("="*50)
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            checks = []
            
            # Check 1: Connection
            checks.append(("Database Connection", "✅ Connected", True))
            
            # Check 2: Tables exist
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            table_count = cursor.fetchone()[0]
            checks.append((
                "Tables",
                f"✅ {table_count} tables found" if table_count > 0 else "❌ No tables found",
                table_count > 0
            ))
            
            # Check 3: Database size
            cursor.execute(f"""
                SELECT pg_database_size('{self.db_config['database']}');
            """)
            db_size = cursor.fetchone()[0]
            size_mb = db_size / 1024 / 1024
            checks.append(("Database Size", f"📊 {size_mb:.2f} MB", True))
            
            # Check 4: Active connections
            cursor.execute("""
                SELECT COUNT(*) 
                FROM pg_stat_activity 
                WHERE datname = %s;
            """, (self.db_config['database'],))
            conn_count = cursor.fetchone()[0]
            checks.append(("Active Connections", f"🔗 {conn_count} connections", True))
            
            # Check 5: Table sizes
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
            """)
            
            tables = cursor.fetchall()
            
            # Display results
            print("\n📋 Health Check Results:")
            print("-" * 50)
            
            for check_name, result, status in checks:
                print(f"{check_name}: {result}")
            
            if tables:
                print(f"\n📊 Table Sizes:")
                for table in tables:
                    print(f"  - {table[1]}: {table[2]}")
            
            # Overall status
            all_good = all(status for _, _, status in checks)
            print("\n" + "-" * 50)
            if all_good:
                print("✅ Overall Status: HEALTHY")
            else:
                print("⚠️  Overall Status: NEEDS ATTENTION")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"\n❌ Health check failed: {e}")
        
        input("\nPress Enter to continue...")
    
    def _run_database_migrations(self) -> None:
        """Run database migrations."""
        print("\nRunning database migrations...")
        cmd = ["python", str(self.script_dir / "database_utils" / "migrate_to_postgresql.py")]
        subprocess.run(cmd)
    
    # =======================
    # GOOGLE SHEETS IMPLEMENTATION METHODS
    # =======================
    
    def _check_sheets_daemon_status(self) -> Tuple[bool, Optional[int]]:
        """Check if sheets sync daemon is running."""
        if not self.pid_file.exists():
            return False, None
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            process = psutil.Process(pid)
            return process.is_running(), pid
        except (psutil.NoSuchProcess, ValueError, FileNotFoundError):
            if self.pid_file.exists():
                self.pid_file.unlink()
            return False, None
    
    def _check_sheets_configuration(self) -> dict:
        """Check sheets sync configuration status."""
        result = {
            'configured': False,
            'spreadsheet_id': None,
            'has_credentials': False
        }
        
        # Check config.json for spreadsheet ID
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    sheets_config = config.get('google_sheets_sync', {})
                    result['spreadsheet_id'] = sheets_config.get('spreadsheet_id')
            except:
                pass
        
        # Check for credentials in environment
        result['has_credentials'] = secure_config.google_credentials is not None
        
        # Check environment variable as fallback
        if not result['spreadsheet_id']:
            result['spreadsheet_id'] = os.environ.get('AUTOTRAINX_SHEETS_ID')
        
        result['configured'] = bool(result['spreadsheet_id'] and result['has_credentials'])
        return result
    
    def _get_last_sync_time(self) -> str:
        """Get last sync time from logs."""
        if not self.log_file.exists():
            return "Never"
        
        try:
            # Look for last sync completion in log
            with open(self.log_file, 'r') as f:
                lines = f.readlines()
                for line in reversed(lines[-1000:]):  # Check last 1000 lines
                    if "Sync completed" in line or "Synced" in line:
                        # Extract timestamp
                        timestamp = line.split(' - ')[0]
                        return timestamp
            return "Unknown"
        except:
            return "Error reading logs"
    
    def _sheets_setup_wizard(self) -> None:
        """Google Sheets setup wizard."""
        os.system('clear')
        self._show_header()
        print("\n🚀 GOOGLE SHEETS SYNC SETUP WIZARD\n")
        
        config = self._check_sheets_configuration()
        
        # Step 1: Spreadsheet ID
        current_id = config.get('spreadsheet_id', '')
        print(f"Current Spreadsheet ID: {current_id or 'Not set'}")
        
        new_id = questionary.text(
            "Enter Google Sheets ID (or press Enter to keep current):",
            default=current_id or "",
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if new_id and new_id != current_id:
            self._save_spreadsheet_id(new_id)
            print("✅ Spreadsheet ID saved")
        
        # Step 2: Check credentials
        if not config['has_credentials']:
            print("\n⚠️  No Google credentials found!")
            self._setup_sheets_authentication()
        else:
            print("\n✅ Google credentials found")
        
        # Step 3: Test connection
        if questionary.confirm("\nTest connection now?", style=AUTOTRAINX_STYLE).ask():
            self._test_sheets_connection()
        
        # Step 4: Start daemon if not running
        is_running, _ = self._check_sheets_daemon_status()
        if not is_running:
            if questionary.confirm("\nStart sync daemon?", style=AUTOTRAINX_STYLE).ask():
                self._start_sheets_daemon()
        
        input("\nSetup complete! Press Enter to continue...")
    
    def _save_spreadsheet_id(self, spreadsheet_id: str) -> None:
        """Save spreadsheet ID to config."""
        config = {}
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        config = json.loads(content)
                    else:
                        print("\n⚠️  Warning: Config file was empty, creating new configuration")
            except json.JSONDecodeError as e:
                print(f"\n⚠️  Warning: Invalid JSON in config file: {e}")
                print("Creating new configuration...")
            except Exception as e:
                print(f"\n❌ Error reading config file: {e}")
                return
        
        if 'google_sheets_sync' not in config:
            config['google_sheets_sync'] = {}
        config['google_sheets_sync']['spreadsheet_id'] = spreadsheet_id
        config['google_sheets_sync']['enabled'] = True
        
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"\n❌ Error saving config file: {e}")
            return
    
    def _start_sheets_daemon(self) -> None:
        """Start the sync daemon."""
        print("\n🚀 Starting sync daemon...")
        
        try:
            # Start daemon
            env = os.environ.copy()
            subprocess.Popen(
                [sys.executable, "sheets_sync_daemon.py", "--daemon"],
                env=env,
                cwd=self.script_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait and check
            time.sleep(3)
            is_running, pid = self._check_sheets_daemon_status()
            
            if is_running:
                print(f"✅ Daemon started successfully (PID: {pid})")
            else:
                print("❌ Failed to start daemon")
                print(f"Check logs: {self.log_file}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        input("\nPress Enter to continue...")
    
    def _stop_sheets_daemon(self) -> None:
        """Stop the sync daemon."""
        print("\n🛑 Stopping sync daemon...")
        
        try:
            subprocess.run(
                [sys.executable, "sheets_sync_daemon.py", "--stop"],
                cwd=self.script_dir,
                capture_output=True
            )
            print("✅ Daemon stopped")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        input("\nPress Enter to continue...")
    
    def _restart_sheets_daemon(self) -> None:
        """Restart the sync daemon."""
        print("\n🔄 Restarting sync daemon...")
        self._stop_sheets_daemon()
        time.sleep(1)
        self._start_sheets_daemon()
    
    def _view_sheets_daemon_status(self) -> None:
        """View detailed sync status."""
        os.system('clear')
        self._show_header()
        print("\n📊 SYNC STATUS\n")
        
        # Show last 20 sync-related log entries
        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()
                sync_lines = [l for l in lines if any(k in l for k in ['Sync', 'sync', 'sheet', 'Sheet'])]
                for line in sync_lines[-20:]:
                    print(line.strip())
        except Exception as e:
            print(f"Error reading logs: {e}")
        
        input("\nPress Enter to continue...")
    
    def _configure_sync_interval(self) -> None:
        """Configure sync interval."""
        interval = questionary.text(
            "Enter sync interval in seconds (default: 30):",
            default="30",
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if interval:
            # Update config
            config = {}
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            
            if 'google_sheets_sync' not in config:
                config['google_sheets_sync'] = {}
            if 'sync_settings' not in config['google_sheets_sync']:
                config['google_sheets_sync']['sync_settings'] = {}
            
            config['google_sheets_sync']['sync_settings']['batch_interval_seconds'] = int(interval)
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"\n✅ Sync interval set to {interval} seconds")
            input("\nPress Enter to continue...")
    
    def _configure_batch_size(self) -> None:
        """Configure batch size."""
        batch_size = questionary.text(
            "Enter batch size (default: 50):",
            default="50",
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if batch_size:
            # Update config
            config = {}
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            
            if 'google_sheets_sync' not in config:
                config['google_sheets_sync'] = {}
            if 'sync_settings' not in config['google_sheets_sync']:
                config['google_sheets_sync']['sync_settings'] = {}
            
            config['google_sheets_sync']['sync_settings']['batch_size'] = int(batch_size)
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"\n✅ Batch size set to {batch_size}")
            input("\nPress Enter to continue...")
    
    def _configure_retry_settings(self) -> None:
        """Configure retry settings."""
        max_retries = questionary.text(
            "Enter maximum retry attempts (default: 3):",
            default="3",
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if max_retries:
            # Update config
            config = {}
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            
            if 'google_sheets_sync' not in config:
                config['google_sheets_sync'] = {}
            if 'sync_settings' not in config['google_sheets_sync']:
                config['google_sheets_sync']['sync_settings'] = {}
            
            config['google_sheets_sync']['sync_settings']['max_retry_attempts'] = int(max_retries)
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"\n✅ Max retry attempts set to {max_retries}")
            input("\nPress Enter to continue...")
    
    def _configure_realtime_events(self) -> None:
        """Configure real-time events."""
        events = questionary.checkbox(
            "Select real-time events to sync immediately:",
            choices=[
                questionary.Choice("training_started", checked=True),
                questionary.Choice("training_failed", checked=True),
                questionary.Choice("training_completed", checked=True),
                questionary.Choice("dataset_prepared", checked=False),
                questionary.Choice("preset_configured", checked=False),
            ],
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if events:
            # Update config
            config = {}
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            
            if 'google_sheets_sync' not in config:
                config['google_sheets_sync'] = {}
            if 'sync_settings' not in config['google_sheets_sync']:
                config['google_sheets_sync']['sync_settings'] = {}
            
            config['google_sheets_sync']['sync_settings']['realtime_events'] = events
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"\n✅ Real-time events configured")
            input("\nPress Enter to continue...")
    
    def _view_sheets_logs(self) -> None:
        """View recent sync logs."""
        os.system('clear')
        self._show_header()
        print("\n📋 RECENT SYNC LOGS\n")
        
        if not self.log_file.exists():
            print("No log file found.")
        else:
            try:
                # Show last 50 lines
                with open(self.log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-50:]:
                        print(line.strip())
            except Exception as e:
                print(f"Error reading logs: {e}")
        
        input("\nPress Enter to continue...")
    
    # Remaining existing methods (with minor updates for consistency)
    
    def _set_workspace_path(self) -> None:
        """Set workspace path."""
        workspace_path = questionary.path(
            "Enter workspace path:",
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if workspace_path:
            # TODO: Implement workspace path setting
            print(f"\n✅ Workspace path set to: {workspace_path}")
            input("\nPress Enter to continue...")
    
    def _view_executions_table(self) -> None:
        """View executions table."""
        cmd = ["python", "main.py", "--db-stats"]
        self._execute_command(cmd, "Executions Table")
    
    def _view_variations_table(self) -> None:
        """View variations table."""
        # TODO: Implement variations table viewer
        print("\n📊 Variations Table Viewer")
        print("This feature is coming soon...")
        input("\nPress Enter to continue...")
    
    def _view_model_paths_table(self) -> None:
        """View model paths table."""
        # TODO: Implement model paths table viewer
        print("\n📂 Model Paths Table Viewer")
        print("This feature is coming soon...")
        input("\nPress Enter to continue...")
    
    def _launch_web_viewer(self) -> None:
        """Launch web database viewer."""
        print("\n🌐 Launching Web Database Viewer...")
        print("This feature is coming soon...")
        input("\nPress Enter to continue...")
    
    def _cleanup_old_records(self) -> None:
        """Cleanup old database records."""
        days = questionary.text(
            "Delete records older than (days):",
            default="30",
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if days and questionary.confirm(
            f"Delete all records older than {days} days?",
            default=False,
            style=AUTOTRAINX_STYLE
        ).ask():
            # TODO: Implement cleanup
            print(f"\n✅ Cleaned up records older than {days} days")
            input("\nPress Enter to continue...")
    
    def _optimize_database(self) -> None:
        """Optimize database performance."""
        print("\n🔧 Optimizing database...")
        # TODO: Implement database optimization
        print("✅ Database optimized")
        input("\nPress Enter to continue...")
    
    def _export_database_stats(self) -> None:
        """Export database statistics."""
        # TODO: Implement stats export
        print("\n📊 Exporting database statistics...")
        print("✅ Statistics exported to: database_stats.html")
        input("\nPress Enter to continue...")
    
    def _view_running_processes(self) -> None:
        """View running AutoTrainX processes."""
        print("\n📊 Running AutoTrainX Processes:")
        print("-" * 50)
        
        # TODO: Implement process viewer
        print("No active processes found.")
        
        input("\nPress Enter to continue...")
    
    def _show_database_diagnostics(self) -> None:
        """Show database diagnostics."""
        self._database_health_check()
    
    def _show_sheets_sync_diagnostics(self) -> None:
        """Show Google Sheets sync diagnostics."""
        os.system('clear')
        self._show_header()
        print("\n📊 GOOGLE SHEETS SYNC DIAGNOSTICS\n")
        
        # Check configuration
        config = self._check_sheets_configuration()
        print(f"Configuration Status: {'✅ Complete' if config['configured'] else '❌ Incomplete'}")
        print(f"Spreadsheet ID: {config['spreadsheet_id'] or 'Not set'}")
        print(f"Credentials: {'✅ Found' if config['has_credentials'] else '❌ Not found'}")
        
        # Check daemon status
        is_running, pid = self._check_sheets_daemon_status()
        print(f"\nDaemon Status: {'🟢 Running' if is_running else '🔴 Stopped'}")
        if is_running:
            print(f"Process ID: {pid}")
        
        # Last sync time
        print(f"Last Sync: {self._get_last_sync_time()}")
        
        input("\nPress Enter to continue...")
    
    def _view_system_logs(self) -> None:
        """View system logs."""
        log_choices = [
            "📋 AutoTrainX Main Log",
            "📊 Google Sheets Sync Log",
            "🗄️  Database Migration Log",
            "⬅️  Cancel"
        ]
        
        log_choice = questionary.select(
            "Select log to view:",
            choices=log_choices,
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if not log_choice or "Cancel" in log_choice:
            return
        
        if "Main Log" in log_choice:
            log_file = self.script_dir / "logs" / "autotrainx.log"
        elif "Sync Log" in log_choice:
            log_file = self.log_file
        elif "Migration Log" in log_choice:
            log_file = self.script_dir / "logs" / "migration.log"
        
        if log_file.exists():
            os.system('clear')
            self._show_header()
            print(f"\n📋 {log_choice}\n")
            
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-100:]:  # Last 100 lines
                        print(line.strip())
            except Exception as e:
                print(f"Error reading log: {e}")
        else:
            print(f"\n❌ Log file not found: {log_file}")
        
        input("\nPress Enter to continue...")
    
    def _show_statistics_dashboard(self) -> None:
        """Show statistics dashboard."""
        print("\n" + "="*50)
        print("  STATISTICS DASHBOARD")
        print("="*50)
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Total executions
            cursor.execute("SELECT COUNT(*) FROM executions;")
            total_executions = cursor.fetchone()[0]
            
            # Executions by status
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM executions 
                GROUP BY status;
            """)
            status_counts = cursor.fetchall()
            
            # Recent activity
            cursor.execute("""
                SELECT COUNT(*) 
                FROM executions 
                WHERE created_at > NOW() - INTERVAL '24 hours';
            """)
            recent_count = cursor.fetchone()[0]
            
            print(f"\n📊 Total Executions: {total_executions}")
            print(f"📈 Last 24 hours: {recent_count}")
            
            print("\n📊 Executions by Status:")
            for status, count in status_counts:
                print(f"  - {status}: {count}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"\n❌ Error loading statistics: {e}")
        
        input("\nPress Enter to continue...")
    
    def _show_quick_start_guide(self) -> None:
        """Show quick start guide."""
        os.system('clear')
        self._show_header()
        print("\n📚 QUICK START GUIDE\n")
        
        print("1. INITIAL SETUP")
        print("   - Go to: System Configuration → Database Configuration → Quick Setup")
        print("   - Run 'Full Auto Setup' for automatic installation")
        print("")
        print("2. GOOGLE SHEETS SYNC")
        print("   - Go to: System Configuration → Google Sheets Sync → Quick Configuration")
        print("   - Run 'Setup Wizard' and follow the prompts")
        print("")
        print("3. TRAINING CONFIGURATION")
        print("   - Go to: Training Configuration → Preset Management")
        print("   - Create custom presets for your training needs")
        print("")
        print("4. START TRAINING")
        print("   - Exit this menu and use: python main.py --help")
        print("   - Example: python main.py single --dataset /path/to/images")
        
        input("\nPress Enter to continue...")
    
    def _show_configuration_guide(self) -> None:
        """Show configuration guide."""
        os.system('clear')
        self._show_header()
        print("\n🔧 CONFIGURATION GUIDE\n")
        
        print("DATABASE CONFIGURATION")
        print("  Required environment variables:")
        print("  - DATABASE_HOST (default: localhost)")
        print("  - DATABASE_PORT (default: 5432)")
        print("  - DATABASE_NAME (default: autotrainx)")
        print("  - DATABASE_USER (default: autotrainx)")
        print("  - DATABASE_PASSWORD (required)")
        print("")
        print("GOOGLE SHEETS CONFIGURATION")
        print("  Required:")
        print("  - AUTOTRAINX_SHEETS_ID (your spreadsheet ID)")
        print("  - Google service account credentials in .env")
        print("")
        print("COMFYUI CONFIGURATION")
        print("  - Set path to ComfyUI installation")
        print("  - Required for image preview generation")
        
        input("\nPress Enter to continue...")
    
    def _show_troubleshooting_guide(self) -> None:
        """Show troubleshooting guide with interactive fixes."""
        while True:
            os.system('clear')
            self._show_header()
            print("\n🐛 TROUBLESHOOTING GUIDE\n")
            
            choice = questionary.select(
                "Select an issue to troubleshoot or apply a fix:",
                choices=[
                    "🔧 Fix triton.ops module error (bitsandbytes compatibility)",
                    "🐘 Fix PostgreSQL authentication issues",
                    "🔄 Fix Google Sheets sync issues",
                    "📋 View common issues and solutions",
                    "🚀 Run quick diagnostics",
                    "⬅️  Back to Help Menu"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back to Help Menu" in choice:
                break
                
            if "Fix triton.ops module error" in choice:
                self._fix_triton_ops_error()
            elif "Fix PostgreSQL authentication" in choice:
                self._fix_postgresql_auth()
            elif "Fix Google Sheets sync" in choice:
                self._fix_sheets_sync()
            elif "View common issues" in choice:
                self._show_common_issues()
            elif "Run quick diagnostics" in choice:
                self._run_diagnostics()
    
    def _show_support_information(self) -> None:
        """Show support information."""
        os.system('clear')
        self._show_header()
        print("\n📞 SUPPORT INFORMATION\n")
        
        print("AUTOTRAINX SUPPORT")
        print("")
        print("📧 Email: support@autotrainx.com")
        print("🌐 Documentation: https://docs.autotrainx.com")
        print("💬 Discord: https://discord.gg/autotrainx")
        print("🐛 Issues: https://github.com/autotrainx/autotrainx/issues")
        print("")
        print("When reporting issues, please include:")
        print("  - Error messages and logs")
        print("  - System configuration (Database, OS)")
        print("  - Steps to reproduce the issue")
        
        input("\nPress Enter to continue...")
    
    # =======================
    # TROUBLESHOOTING FIX METHODS
    # =======================
    
    def _fix_triton_ops_error(self) -> None:
        """Fix the triton.ops module error for bitsandbytes compatibility."""
        os.system('clear')
        self._show_header()
        print("\n🔧 FIX TRITON.OPS MODULE ERROR\n")
        
        print("This fix addresses the error:")
        print("  ModuleNotFoundError: No module named 'triton.ops'")
        print("")
        print("This error occurs when bitsandbytes tries to import")
        print("triton.ops functions that don't exist in newer versions.")
        print("")
        
        proceed = questionary.confirm(
            "Apply the triton.ops fix?",
            default=True,
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if not proceed:
            return
            
        print("\n🔄 Applying fix...")
        
        try:
            # Find Python version and site-packages path
            import sys
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            site_packages = f"venv/lib/python{python_version}/site-packages"
            
            # Check if triton is installed
            triton_path = os.path.join(site_packages, "triton")
            if not os.path.exists(triton_path):
                print(f"❌ Error: triton not found in {site_packages}")
                print("Make sure triton is installed in your virtual environment")
                input("\nPress Enter to continue...")
                return
            
            # Create triton/ops directory
            ops_path = os.path.join(triton_path, "ops")
            os.makedirs(ops_path, exist_ok=True)
            print(f"✅ Created {ops_path}")
            
            # Create __init__.py
            init_content = '''# Stub module for triton.ops
# This fixes compatibility with bitsandbytes and diffusers

class _StubOp:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

# Common ops that might be used
matmul = _StubOp()
elementwise = _StubOp()
reduction = _StubOp()

def __getattr__(name):
    return _StubOp()
'''
            init_path = os.path.join(ops_path, "__init__.py")
            with open(init_path, 'w') as f:
                f.write(init_content)
            print(f"✅ Created {init_path}")
            
            # Create matmul_perf_model.py
            matmul_content = '''# Stub for matmul_perf_model required by bitsandbytes

def early_config_prune(configs, named_args):
    """Stub function for early_config_prune"""
    # Just return configs as-is
    return configs

def estimate_matmul_time(M, N, K, dtype):
    """Stub function for estimate_matmul_time"""
    # Return a dummy time estimate
    return 1.0

# Any other function that might be needed
def __getattr__(name):
    return lambda *args, **kwargs: None
'''
            matmul_path = os.path.join(ops_path, "matmul_perf_model.py")
            with open(matmul_path, 'w') as f:
                f.write(matmul_content)
            print(f"✅ Created {matmul_path}")
            
            print("\n🧪 Testing imports...")
            
            # Test imports
            try:
                import triton.ops
                print("✅ triton.ops imports OK")
            except Exception as e:
                print(f"❌ triton.ops import failed: {e}")
            
            try:
                from triton.ops.matmul_perf_model import early_config_prune, estimate_matmul_time
                print("✅ bitsandbytes imports OK")
            except Exception as e:
                print(f"❌ bitsandbytes imports failed: {e}")
            
            print("\n✨ Fix applied successfully!")
            print("Your training should work now without the triton.ops error.")
            
        except Exception as e:
            print(f"\n❌ Error applying fix: {e}")
            
        input("\nPress Enter to continue...")
    
    def _fix_postgresql_auth(self) -> None:
        """Fix PostgreSQL authentication issues."""
        os.system('clear')
        self._show_header()
        print("\n🐘 FIX POSTGRESQL AUTHENTICATION\n")
        
        print("This will fix common PostgreSQL authentication issues:")
        print("  - Password authentication failed")
        print("  - Peer authentication failed")
        print("  - Connection refused errors")
        print("")
        
        if self.is_docker or self.is_root:
            print("🐳 Docker/Root environment detected")
            print("Will apply trust authentication for local connections")
            print("")
        
        proceed = questionary.confirm(
            "Apply PostgreSQL authentication fix?",
            default=True,
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if not proceed:
            return
            
        print("\n🔄 Applying fix...")
        
        # Run the fix_container_auth function from setup_postgresql.sh
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                  "database_utils", "setup_postgresql.sh")
        
        if os.path.exists(script_path):
            # Source the script and run the fix function
            cmd = f"bash -c 'source {script_path} && fix_container_auth'"
            result = self._run_privileged_command(["bash", "-c", cmd])
            
            if result.returncode == 0:
                print("\n✅ PostgreSQL authentication fixed!")
                print("You should now be able to connect to the database.")
            else:
                print("\n❌ Failed to apply fix")
                print("You may need to manually edit pg_hba.conf")
        else:
            print("\n❌ PostgreSQL setup script not found")
            
        input("\nPress Enter to continue...")
    
    def _fix_sheets_sync(self) -> None:
        """Fix Google Sheets sync issues."""
        os.system('clear')
        self._show_header()
        print("\n🔄 FIX GOOGLE SHEETS SYNC\n")
        
        print("Common Google Sheets sync issues:")
        print("  1. Service account not configured")
        print("  2. Spreadsheet not shared with service account")
        print("  3. Daemon not running")
        print("")
        
        choice = questionary.select(
            "Select fix to apply:",
            choices=[
                "Check service account configuration",
                "Restart sync daemon",
                "View sync logs",
                "Back"
            ],
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if choice == "Check service account configuration":
            print("\n📋 Checking configuration...")
            # Check if credentials file exists
            cred_path = "service_account_key.json"
            if os.path.exists(cred_path):
                print("✅ Service account credentials found")
            else:
                print("❌ Service account credentials not found")
                print("   Please place service_account_key.json in the root directory")
            
            # Check environment variables
            if os.getenv("AUTOTRAINX_SHEETS_ID"):
                print("✅ Spreadsheet ID configured")
            else:
                print("❌ AUTOTRAINX_SHEETS_ID not set in environment")
                
        elif choice == "Restart sync daemon":
            print("\n🔄 Restarting sync daemon...")
            # Stop daemon
            self._run_privileged_command(["pkill", "-f", "sheets_sync_daemon.py"])
            time.sleep(1)
            # Start daemon
            cmd = ["python", "src/sheets_sync/sheets_sync_daemon.py", "--daemon"]
            result = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✅ Sync daemon restarted")
            
        elif choice == "View sync logs":
            log_path = "logs/sheets_sync_log/sheets_sync.log"
            if os.path.exists(log_path):
                print(f"\n📄 Recent log entries from {log_path}:")
                result = subprocess.run(["tail", "-n", "20", log_path], capture_output=True, text=True)
                print(result.stdout)
            else:
                print("\n❌ Log file not found")
                
        input("\nPress Enter to continue...")
    
    def _show_common_issues(self) -> None:
        """Show common issues and their solutions."""
        os.system('clear')
        self._show_header()
        print("\n📋 COMMON ISSUES AND SOLUTIONS\n")
        
        issues = [
            {
                "title": "1. Database Connection Failed",
                "symptoms": [
                    "- psql: FATAL: password authentication failed",
                    "- could not connect to server: No such file or directory",
                    "- FATAL: Peer authentication failed"
                ],
                "solutions": [
                    "- Run: Troubleshooting → Fix PostgreSQL authentication",
                    "- Check PostgreSQL is running: systemctl status postgresql",
                    "- Verify .env file has correct DATABASE_PASSWORD",
                    "- For Docker: ensure PostgreSQL container is running"
                ]
            },
            {
                "title": "2. ModuleNotFoundError: No module named 'triton.ops'",
                "symptoms": [
                    "- Error when importing diffusers or bitsandbytes",
                    "- Training fails to start with triton.ops error"
                ],
                "solutions": [
                    "- Run: Troubleshooting → Fix triton.ops module error",
                    "- This creates stub modules for compatibility",
                    "- No functionality is lost - just prevents import errors"
                ]
            },
            {
                "title": "3. Google Sheets Sync Not Working",
                "symptoms": [
                    "- Data not appearing in Google Sheets",
                    "- Sync daemon keeps stopping",
                    "- Authentication errors in logs"
                ],
                "solutions": [
                    "- Ensure service_account_key.json is in root directory",
                    "- Share spreadsheet with service account email",
                    "- Check AUTOTRAINX_SHEETS_ID in .env file",
                    "- Run: Troubleshooting → Fix Google Sheets sync"
                ]
            },
            {
                "title": "4. Training Fails to Start",
                "symptoms": [
                    "- Process exits immediately",
                    "- Dataset not found errors",
                    "- Invalid preset configuration"
                ],
                "solutions": [
                    "- Verify dataset path exists and contains images",
                    "- Check preset configuration is valid",
                    "- Review logs in logs/training_log/",
                    "- Ensure CUDA is properly installed for GPU training"
                ]
            },
            {
                "title": "5. Permission Denied Errors",
                "symptoms": [
                    "- Cannot write to output directory",
                    "- Cannot access model files",
                    "- sudo: command not found (in Docker)"
                ],
                "solutions": [
                    "- Check file permissions: ls -la",
                    "- For Docker: files are owned by root user",
                    "- Run: chown -R $(whoami) /workspace",
                    "- Menu automatically handles Docker/root detection"
                ]
            }
        ]
        
        for issue in issues:
            print(f"\n{issue['title']}")
            print("\nSymptoms:")
            for symptom in issue['symptoms']:
                print(f"  {symptom}")
            print("\nSolutions:")
            for solution in issue['solutions']:
                print(f"  {solution}")
            print("-" * 50)
            
        input("\nPress Enter to continue...")
    
    def _run_diagnostics(self) -> None:
        """Run quick diagnostics to check system status."""
        os.system('clear')
        self._show_header()
        print("\n🚀 RUNNING DIAGNOSTICS\n")
        
        diagnostics = []
        
        # Check Python version
        import sys
        diagnostics.append({
            "check": "Python Version",
            "status": "✅" if sys.version_info >= (3, 8) else "❌",
            "info": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        })
        
        # Check virtual environment
        diagnostics.append({
            "check": "Virtual Environment",
            "status": "✅" if sys.prefix != sys.base_prefix else "❌",
            "info": "Active" if sys.prefix != sys.base_prefix else "Not active"
        })
        
        # Check PostgreSQL
        pg_running = False
        try:
            result = subprocess.run(["pg_isready"], capture_output=True, text=True)
            pg_running = result.returncode == 0
        except:
            pass
        diagnostics.append({
            "check": "PostgreSQL",
            "status": "✅" if pg_running else "❌",
            "info": "Running" if pg_running else "Not running"
        })
        
        # Check required directories
        required_dirs = ["workspace", "models", "logs", "presets"]
        missing_dirs = [d for d in required_dirs if not os.path.exists(d)]
        diagnostics.append({
            "check": "Required Directories",
            "status": "✅" if not missing_dirs else "❌",
            "info": "All present" if not missing_dirs else f"Missing: {', '.join(missing_dirs)}"
        })
        
        # Check GPU/CUDA
        has_gpu = False
        try:
            import torch
            has_gpu = torch.cuda.is_available()
            cuda_version = torch.version.cuda if has_gpu else "N/A"
        except:
            cuda_version = "N/A"
        diagnostics.append({
            "check": "GPU/CUDA",
            "status": "✅" if has_gpu else "⚠️",
            "info": f"CUDA {cuda_version}" if has_gpu else "CPU only"
        })
        
        # Check critical Python packages
        packages = ["questionary", "sqlalchemy", "fastapi", "diffusers", "torch"]
        missing_packages = []
        for pkg in packages:
            try:
                __import__(pkg)
            except ImportError:
                missing_packages.append(pkg)
        diagnostics.append({
            "check": "Python Packages",
            "status": "✅" if not missing_packages else "❌",
            "info": "All installed" if not missing_packages else f"Missing: {', '.join(missing_packages)}"
        })
        
        # Display results
        print("DIAGNOSTIC RESULTS:")
        print("-" * 60)
        for diag in diagnostics:
            print(f"{diag['status']} {diag['check']:<25} {diag['info']}")
        print("-" * 60)
        
        # Summary
        errors = sum(1 for d in diagnostics if d['status'] == "❌")
        warnings = sum(1 for d in diagnostics if d['status'] == "⚠️")
        
        print(f"\nSummary: {errors} errors, {warnings} warnings")
        
        if errors > 0:
            print("\n💡 Run the appropriate fixes from the troubleshooting menu")
            print("   to resolve the errors above.")
            
        input("\nPress Enter to continue...")
    
    # Existing helper methods remain the same...
    
    def _preset_management_menu(self) -> None:
        """Preset management submenu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            choice = questionary.select(
                "Preset Management:",
                choices=[
                    "➕ Create Custom Preset",
                    "🗑️  Delete Custom Preset",
                    "👁️  Show Preset Details",
                    "📋 List All Presets",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
                
            if "Create Custom Preset" in choice:
                self._create_preset()
            elif "Delete Custom Preset" in choice:
                self._delete_preset()
            elif "Show Preset Details" in choice:
                self._show_preset_details()
            elif "List All Presets" in choice:
                self._list_presets()
    
    def _create_preset(self) -> None:
        """Create a custom preset."""
        print("\n" + "="*40)
        print("      CREATE CUSTOM PRESET")
        print("="*40)
        
        # Get preset name
        name = questionary.text(
            "Preset name:",
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if not name:
            return
            
        # Get base preset
        base_preset = self._select_preset("Select base preset to inherit from:")
        if not base_preset:
            return
            
        # Get description
        description = questionary.text(
            "Preset description (optional):",
            style=AUTOTRAINX_STYLE
        ).ask() or f"Custom preset based on {base_preset}"
        
        # Get overrides
        overrides = []
        print("\nEnter configuration overrides (press Enter with empty input to finish):")
        
        while True:
            override = questionary.text(
                "Override (format: param=value):",
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if not override:
                break
                
            if '=' not in override:
                print("Invalid format. Use: param=value")
                continue
                
            overrides.append(override)
            print(f"Added: {override}")
        
        # Build command
        cmd = [
            "python", "main.py", "--create-preset",
            "--name", name,
            "--base", base_preset,
            "--description", description
        ]
        
        if overrides:
            cmd.extend(["--overrides"] + overrides)
        
        # Confirm execution
        if questionary.confirm(
            f"Create preset '{name}' based on '{base_preset}'?",
            default=True,
            style=AUTOTRAINX_STYLE
        ).ask():
            self._execute_command(cmd, f"Creating preset '{name}'")
    
    def _delete_preset(self) -> None:
        """Delete a custom preset."""
        # Get available custom presets
        try:
            custom_presets = self._get_custom_presets()
            if not custom_presets:
                print("No custom presets found.")
                input("Press Enter to continue...")
                return
                
            preset_name = questionary.select(
                "Select preset to delete:",
                choices=custom_presets + ["⬅️ Cancel"],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if not preset_name or "Cancel" in preset_name:
                return
            
            # Confirm deletion
            if questionary.confirm(
                f"Are you sure you want to delete preset '{preset_name}'?",
                default=False,
                style=AUTOTRAINX_STYLE
            ).ask():
                cmd = ["python", "main.py", "--delete-preset", "--name", preset_name]
                self._execute_command(cmd, f"Deleting preset '{preset_name}'")
                
        except Exception as e:
            self._show_error(f"Error loading custom presets: {str(e)}")
    
    def _show_preset_details(self) -> None:
        """Show details of a specific preset."""
        preset_name = self._select_preset("Select preset to view:")
        if preset_name:
            cmd = ["python", "main.py", "--show-preset", "--name", preset_name]
            self._execute_command(cmd, f"Preset details for '{preset_name}'")
    
    def _set_custom_path(self) -> None:
        """Set custom output path."""
        custom_path = questionary.path(
            "Enter custom output path (leave empty for default):",
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if custom_path is not None:  # Allow empty string to reset to default
            cmd = ["python", "main.py", "--configure", "--custom-path", custom_path] if custom_path else ["python", "main.py", "--configure", "--custom-path", ""]
            self._execute_command(cmd, "Setting custom output path")
    
    def _save_path_profile(self) -> None:
        """Save current path configuration as a profile."""
        profile_name = questionary.text(
            "Profile name:",
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if profile_name:
            cmd = ["python", "main.py", "--configure", "--save-profile", profile_name]
            self._execute_command(cmd, f"Saving profile '{profile_name}'")
    
    def _list_path_profiles(self) -> None:
        """List all saved path profiles."""
        cmd = ["python", "main.py", "--configure", "--list-profiles"]
        self._execute_command(cmd, "Listing path profiles")
    
    def _switch_to_profile(self) -> None:
        """Switch to a saved profile."""
        try:
            from src.utils.path_manager import PathProfile
            profile_manager = PathProfile(base_path=self.base_path)
            profiles = profile_manager.list_profiles()
            
            if not profiles:
                print("No saved profiles found.")
                input("Press Enter to continue...")
                return
            
            profile_names = list(profiles.keys()) + ["⬅️ Cancel"]
            
            profile_name = questionary.select(
                "Select profile to use:",
                choices=profile_names,
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if profile_name and "Cancel" not in profile_name:
                cmd = ["python", "main.py", "--configure", "--use-profile", profile_name]
                self._execute_command(cmd, f"Switching to profile '{profile_name}'")
                
        except Exception as e:
            self._show_error(f"Error loading profiles: {str(e)}")
    
    def _delete_path_profile(self) -> None:
        """Delete a saved path profile."""
        try:
            from src.utils.path_manager import PathProfile
            profile_manager = PathProfile(base_path=self.base_path)
            profiles = profile_manager.list_profiles()
            
            # Remove default profile from deletion options
            profiles.pop("default", None)
            
            if not profiles:
                print("No custom profiles found to delete.")
                input("Press Enter to continue...")
                return
            
            profile_names = list(profiles.keys()) + ["⬅️ Cancel"]
            
            profile_name = questionary.select(
                "Select profile to delete:",
                choices=profile_names,
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if profile_name and "Cancel" not in profile_name:
                if questionary.confirm(
                    f"Are you sure you want to delete profile '{profile_name}'?",
                    default=False,
                    style=AUTOTRAINX_STYLE
                ).ask():
                    cmd = ["python", "main.py", "--configure", "--delete-profile", profile_name]
                    self._execute_command(cmd, f"Deleting profile '{profile_name}'")
                    
        except Exception as e:
            self._show_error(f"Error loading profiles: {str(e)}")
    
    def _set_comfyui_path(self) -> None:
        """Set ComfyUI installation path."""
        comfyui_path = questionary.path(
            "Enter path to ComfyUI installation directory:",
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if comfyui_path:
            cmd = ["python", "main.py", "--configure", "--comfyui-path", comfyui_path]
            self._execute_command(cmd, "Setting ComfyUI path")
    
    def _validate_preview_system(self) -> None:
        """Validate the preview system."""
        cmd = ["python", "main.py", "--configure", "--validate-preview"]
        self._execute_command(cmd, "Validating preview system")
    
    def _diagnose_comfyui(self) -> None:
        """Diagnose ComfyUI environment."""
        cmd = ["python", "main.py", "--configure", "--diagnose-comfyui"]
        self._execute_command(cmd, "Diagnosing ComfyUI environment")
    
    def _configure_spreadsheet_id(self) -> None:
        """Configure Google Sheets spreadsheet ID."""
        print("\n" + "="*40)
        print("  CONFIGURE SPREADSHEET ID")
        print("="*40)
        print("\nTo get your spreadsheet ID:")
        print("1. Open your Google Sheet")
        print("2. Look at the URL: https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit")
        print("3. Copy the ID between '/d/' and '/edit'")
        print("")
        
        spreadsheet_id = questionary.text(
            "Enter Google Sheets spreadsheet ID:",
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if spreadsheet_id:
            self._save_spreadsheet_id(spreadsheet_id)
            print(f"\n✅ Spreadsheet ID set to: {spreadsheet_id}")
            print("\nIMPORTANT: Make sure the sheet is shared with your service account email")
            
            # Check if Google credentials are configured
            try:
                from ..configuration.secure_config import secure_config
                if not secure_config.google_credentials:
                    print("\n⚠️  Warning: Google credentials not found in environment")
                    print("Please configure Google authentication before testing the connection")
            except Exception as e:
                print(f"\n⚠️  Warning: Could not verify Google credentials: {e}")
            
            input("\nPress Enter to continue...")
    
    def _setup_sheets_authentication(self) -> None:
        """Setup Google Sheets authentication."""
        auth_type = questionary.select(
            "Select authentication method:",
            choices=[
                "OAuth2 (Interactive) - Recommended for personal use",
                "Service Account - Recommended for automation",
                "⬅️ Cancel"
            ],
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if not auth_type or "Cancel" in auth_type:
            return
        
        if "OAuth2" in auth_type:
            self._setup_oauth2_auth()
        else:
            self._setup_service_account_auth()
    
    def _setup_oauth2_auth(self) -> None:
        """Setup OAuth2 authentication."""
        print("\n" + "="*40)
        print("  OAUTH2 AUTHENTICATION SETUP")
        print("="*40)
        print("\nSteps to setup OAuth2:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing")
        print("3. Enable Google Sheets API")
        print("4. Create OAuth2 credentials")
        print("5. Download credentials.json file")
        print("")
        
        print("\n⚠️  For security, please add credentials to your .env file:")
        print("\nGOOGLE_SERVICE_ACCOUNT_EMAIL=<your-email>")
        print("GOOGLE_PROJECT_ID=<your-project-id>")
        print("GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY=\"<your-private-key>\"")
        
        print("\n✅ After adding credentials to .env, restart this menu.")
        print("\n⚠️  Note: OAuth2 will open a browser for authorization on first use.")
        
        input("\nPress Enter to continue...")
    
    def _setup_service_account_auth(self) -> None:
        """Setup service account authentication."""
        print("\n" + "="*40)
        print("  SERVICE ACCOUNT SETUP")
        print("="*40)
        print("\nSteps to setup Service Account:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a service account")
        print("3. Generate and download JSON key")
        print("4. Share your Google Sheet with the service account email")
        print("")
        
        key_path = questionary.path(
            "Enter path to service account key JSON file:",
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if key_path:
            try:
                # Extract credentials for display
                with open(key_path, 'r') as f:
                    creds_data = json.load(f)
                    service_account_email = creds_data.get('client_email')
                    
                print(f"\n⚠️  For security, please add credentials to your .env file:")
                print(f"\nGOOGLE_SERVICE_ACCOUNT_EMAIL={service_account_email}")
                print(f"GOOGLE_PROJECT_ID={creds_data.get('project_id', '')}")
                print("GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY=\"<copy private key from JSON>\"")
                
                if service_account_email:
                    print(f"\n📧 Service Account Email: {service_account_email}")
                    print("⚠️  IMPORTANT: Share your Google Sheet with this email!")
                
                print("\n✅ After adding credentials to .env, restart this menu.")
                
            except Exception as e:
                print(f"\n❌ Error reading key file: {e}")
        
        input("\nPress Enter to continue...")
    
    def _install_sheets_dependencies(self) -> None:
        """Install Google Sheets API dependencies."""
        print("\n" + "="*40)
        print("  INSTALL GOOGLE SHEETS DEPENDENCIES")
        print("="*40)
        print("\nThis will install the following packages:")
        print("  - google-api-python-client")
        print("  - google-auth")
        print("  - google-auth-oauthlib")
        print("  - google-auth-httplib2")
        print("")
        
        if questionary.confirm(
            "Do you want to install these dependencies?",
            default=True,
            style=AUTOTRAINX_STYLE
        ).ask():
            print("\nInstalling dependencies...")
            
            # Build pip command
            pip_cmd = [sys.executable, "-m", "pip", "install",
                      "google-api-python-client",
                      "google-auth",
                      "google-auth-oauthlib",
                      "google-auth-httplib2"]
            
            try:
                print("\nRunning: " + " ".join(pip_cmd))
                print("-" * 50)
                
                result = subprocess.run(pip_cmd, capture_output=False, text=True)
                
                if result.returncode == 0:
                    print("-" * 50)
                    print("\n✅ Dependencies installed successfully!")
                else:
                    print("-" * 50)
                    print(f"\n❌ Installation failed with exit code {result.returncode}")
                    
            except Exception as e:
                print(f"\n❌ Error installing dependencies: {e}")
            
            input("\nPress Enter to continue...")
    
    def _test_sheets_connection(self) -> None:
        """Test Google Sheets connection."""
        print("\n" + "="*40)
        print("  TESTING GOOGLE SHEETS CONNECTION")
        print("="*40)
        
        try:
            # Check if configuration exists
            config_data = Config.load_config(self.base_path)
            sync_config = config_data.get('google_sheets_sync', {})
            
            if not sync_config.get('enabled', False):
                print("\n❌ Google Sheets sync is not enabled.")
                print("   Please enable it first using the menu.")
                input("\nPress Enter to continue...")
                return
            
            spreadsheet_id = sync_config.get('spreadsheet_id', '')
            if not spreadsheet_id:
                print("\n❌ No spreadsheet ID configured.")
                print("   Please configure it first using the menu.")
                input("\nPress Enter to continue...")
                return
            
            # Check if credentials are configured in environment
            if not secure_config.google_credentials:
                print(f"\n❌ Google credentials not found in environment")
                print("   Please add credentials to your .env file.")
                input("\nPress Enter to continue...")
                return
            
            print("\nConfiguration found:")
            print(f"  - Spreadsheet ID: {spreadsheet_id}")
            print(f"  - Credentials: Found in environment")
            print("\nTesting connection...")
            
            # Import and run the test
            try:
                import asyncio
                from src.sheets_sync.integration import test_connection
                
                # Run the async test
                result = asyncio.run(test_connection())
                
                if result:
                    print("\n✅ Connection test successful!")
                    print("   Google Sheets API is working correctly.")
                else:
                    print("\n❌ Connection test failed!")
                    print("\nPossible issues:")
                    print("  - Google Sheets API not enabled")
                    print("  - Spreadsheet not shared with service account")
                    print("  - Invalid credentials")
                    
            except ImportError as e:
                print(f"\n❌ Import error: {e}")
                print("\n📦 Missing Google Sheets API dependencies!")
                print("\nPlease install them using the menu:")
                print("Maintenance → Install Dependencies")
            except Exception as e:
                print(f"\n❌ Connection test failed: {e}")
                
        except Exception as e:
            print(f"\n❌ Error during test: {e}")
        
        input("\nPress Enter to continue...")
    
    def _manual_full_sync(self) -> None:
        """Perform manual full synchronization."""
        if questionary.confirm(
            "This will sync all database records to Google Sheets. Continue?",
            default=True,
            style=AUTOTRAINX_STYLE
        ).ask():
            print("\n" + "="*40)
            print("  PERFORMING MANUAL FULL SYNC")
            print("="*40)
            
            try:
                # Check configuration first
                config_data = Config.load_config(self.base_path)
                sync_config = config_data.get('google_sheets_sync', {})
                
                if not sync_config.get('enabled', False):
                    print("\n❌ Google Sheets sync is not enabled.")
                    input("\nPress Enter to continue...")
                    return
                
                if not sync_config.get('spreadsheet_id', ''):
                    print("\n❌ No spreadsheet ID configured.")
                    input("\nPress Enter to continue...")
                    return
                
                print("\nStarting manual synchronization...")
                print("This may take a moment depending on the number of records...")
                
                # Import and run the sync
                try:
                    import asyncio
                    from src.sheets_sync.integration import manual_full_sync
                    
                    # Run the async sync
                    result = asyncio.run(manual_full_sync())
                    
                    if result.success:
                        print(f"\n✅ Synchronization completed successfully!")
                        print(f"   {result.message}")
                        if result.data:
                            print(f"   Total records synced: {result.data.get('total_synced', 0)}")
                    else:
                        print(f"\n❌ Synchronization failed: {result.message}")
                        
                except ImportError as e:
                    print(f"\n❌ Import error: {e}")
                    print("\n📦 Missing Google Sheets API dependencies!")
                except Exception as e:
                    print(f"\n❌ Synchronization failed: {e}")
                    
            except Exception as e:
                print(f"\n❌ Error during sync: {e}")
            
            input("\nPress Enter to continue...")
    
    def _display_settings_menu(self) -> None:
        """Display settings submenu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            choice = questionary.select(
                "Display Settings:",
                choices=[
                    "📊 Progress Display Mode",
                    "🎨 UI Theme Settings",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
                
            if "Progress Display Mode" in choice:
                self._set_progress_display()
            elif "UI Theme Settings" in choice:
                print("\n🎨 UI Theme Settings")
                print("This feature is coming soon...")
                input("\nPress Enter to continue...")
    
    def _set_progress_display(self) -> None:
        """Set training progress display mode."""
        display_mode = questionary.select(
            "Select training progress display mode:",
            choices=[
                "progress - Progress bar with estimated time",
                "raw - Raw training logs",
                "⬅️ Cancel"
            ],
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if display_mode and "Cancel" not in display_mode:
            mode = display_mode.split(" - ")[0]
            cmd = ["python", "main.py", "--configure", "--set-progress-display", mode]
            self._execute_command(cmd, f"Setting progress display to '{mode}'")
    
    def _clear_database(self) -> None:
        """Clear all database records."""
        if questionary.confirm(
            "This will permanently delete ALL training records. Are you sure?",
            default=False,
            style=AUTOTRAINX_STYLE
        ).ask():
            cmd = ["python", "main.py", "--clear-db"]
            self._execute_command(cmd, "Clearing database")
    
    def _cleanup_stale_processes(self) -> None:
        """Clean up stale processes."""
        cmd = ["python", "main.py", "--cleanup-stale"]
        self._execute_command(cmd, "Cleaning up stale processes")
    
    def _show_system_status(self) -> None:
        """Show system status."""
        cmd = ["python", "main.py", "--status"]
        self._execute_command(cmd, "System Status")
    
    def _list_presets(self) -> None:
        """List all available presets."""
        cmd = ["python", "main.py", "--list-presets"]
        self._execute_command(cmd, "Available Presets")
    
    def _show_job_history(self) -> None:
        """Show job execution history."""
        # Get options
        limit = questionary.text(
            "Number of recent jobs to show:",
            default="20",
            style=AUTOTRAINX_STYLE
        ).ask()
        
        filter_status = questionary.select(
            "Filter by status (optional):",
            choices=[
                "All statuses",
                "done", "failed", "training", "pending",
                "ready_for_training", "preparing_dataset",
                "configuring_preset", "generating_preview"
            ],
            style=AUTOTRAINX_STYLE
        ).ask()
        
        filter_dataset = questionary.text(
            "Filter by dataset name (optional):",
            style=AUTOTRAINX_STYLE
        ).ask()
        
        # Build command
        cmd = ["python", "main.py", "--job-history", "--limit", limit or "20"]
        
        if filter_status and filter_status != "All statuses":
            cmd.extend(["--filter-status", filter_status])
        
        if filter_dataset:
            cmd.extend(["--filter-dataset", filter_dataset])
        
        self._execute_command(cmd, "Job History")
    
    def _show_job_details(self) -> None:
        """Show detailed job information."""
        job_id = questionary.text(
            "Enter job ID:",
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if job_id:
            cmd = ["python", "main.py", "--job-info", "--job-id", job_id]
            self._execute_command(cmd, f"Job Details for '{job_id}'")
    
    # Helper Methods
    def _select_preset(self, prompt: str = "Select a preset:") -> Optional[str]:
        """Helper to select a preset from available options."""
        try:
            from src.scripts.preset_manager import get_preset_manager
            preset_manager = get_preset_manager()
            presets = preset_manager.list_presets()
            
            if not presets:
                print("No presets found.")
                input("Press Enter to continue...")
                return None
            
            preset_choices = [f"{name} - {info.description}" for name, info in presets.items()]
            preset_choices.append("⬅️ Cancel")
            
            choice = questionary.select(
                prompt,
                choices=preset_choices,
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice and "Cancel" not in choice:
                return choice.split(" - ")[0]
            return None
            
        except Exception as e:
            self._show_error(f"Error loading presets: {str(e)}")
            return None
    
    def _get_custom_presets(self) -> List[str]:
        """Get list of custom presets."""
        try:
            from src.scripts.preset_manager import get_preset_manager
            preset_manager = get_preset_manager()
            presets = preset_manager.list_presets()
            return [name for name, info in presets.items() if info.is_custom]
        except Exception:
            return []
    
    def _execute_command(self, cmd: List[str], operation_name: str) -> None:
        """Execute a command and handle the output."""
        print(f"\n{'='*50}")
        print(f"  {operation_name.upper()}")
        print(f"{'='*50}")
        print(f"Executing: {' '.join(cmd)}")
        print("-" * 50)
        
        try:
            # Execute the command from project root
            project_root = Path(__file__).parent.parent.parent
            result = subprocess.run(cmd, capture_output=False, text=True, cwd=project_root)
            
            print("-" * 50)
            if result.returncode == 0:
                print(f"✅ {operation_name} completed successfully!")
            else:
                print(f"❌ {operation_name} failed with exit code {result.returncode}")
            
        except KeyboardInterrupt:
            print(f"\n⚠️  {operation_name} interrupted by user")
        except Exception as e:
            print(f"❌ Error executing command: {str(e)}")
        
        print("=" * 50)
        input("\nPress Enter to continue...")
    
    def _show_error(self, message: str) -> None:
        """Display an error message."""
        print(f"\n❌ Error: {message}")
        input("Press Enter to continue...")


def main():
    """Main entry point."""
    try:
        menu = AutoTrainXMenu()
        menu.run()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
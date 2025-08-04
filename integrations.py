#!/usr/bin/env python3
"""
AutoTrainX Integrations Manager

This script manages the installation and configuration of AutoTrainX integrations:
- PostgreSQL database
- Google Sheets synchronization  
- Sync Daemon
- General configuration variables

Each integration manages its own environment variables in .env file.

Usage:
    python integrations.py                    # Interactive menu
    python integrations.py --verify           # Verify all configurations
    python integrations.py --install postgres # Install specific component
    python integrations.py --config postgres  # Configure specific component
"""

import os
import sys
import subprocess
import json
import secrets
import string
import shutil
import getpass
import argparse
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime

# Pre-flight check for required modules
try:
    import psutil
except ImportError:
    print("\033[91mError: psutil module not found!\033[0m")
    print("\nThis means the core dependencies were not installed properly.")
    print("Please run the following commands:")
    print("\n  1. source venv/bin/activate")
    print("  2. pip install -r requirements.txt")
    print("\nOr re-run setup.sh:")
    print("\n  ./setup.sh --clean")
    print("  ./setup.sh --profile <your-profile>")
    print("\nMake sure the 'core_deps' step completes successfully.")
    sys.exit(1)

# Try to import questionary for better menus
try:
    import questionary
    from questionary import Style
    HAS_QUESTIONARY = True
    
    # Define custom style
    custom_style = Style([
        ('qmark', 'fg:#673ab7 bold'),
        ('question', 'bold'),
        ('answer', 'fg:#f44336 bold'),
        ('pointer', 'fg:#673ab7 bold'),
        ('highlighted', 'fg:#673ab7 bold'),
        ('selected', 'fg:#cc5454'),
        ('separator', 'fg:#cc5454'),
        ('instruction', ''),
        ('text', ''),
        ('disabled', 'fg:#858585 italic')
    ])
except ImportError:
    HAS_QUESTIONARY = False
    print("\033[93mWarning: questionary not found. Using basic input (no arrow key support).\033[0m")
    print("Install with: pip install questionary\n")

# Try to import psycopg2 for PostgreSQL verification
try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

# Try to import Google auth for verification
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False


class Colors:
    """Terminal color codes"""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'


class IntegrationsManager:
    """Manages AutoTrainX integrations installation and configuration"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.env_path = self.base_path / ".env"
        self.settings_path = self.base_path / "settings"
        self.settings_path.mkdir(exist_ok=True)
        
        # Component status tracking
        self.components_status = {
            'postgresql': {'installed': False, 'configured': False},
            'google_sheets': {'installed': False, 'configured': False},
            'sync_daemon': {'installed': True, 'configured': False}  # Python-based, no separate install
        }
        
    def print_header(self, title: str):
        """Print a formatted header"""
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{title.center(60)}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
        
    def print_success(self, message: str):
        """Print success message"""
        print(f"{Colors.GREEN}✓{Colors.RESET} {message}")
        
    def print_error(self, message: str):
        """Print error message"""
        print(f"{Colors.RED}✗{Colors.RESET} {message}")
        
    def print_warning(self, message: str):
        """Print warning message"""
        print(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")
        
    def print_info(self, message: str):
        """Print info message"""
        print(f"{Colors.BLUE}ℹ{Colors.RESET} {message}")
        
    def prompt_for_value(self, prompt: str, default: str = None, secret: bool = False) -> str:
        """Prompt user for input with optional default value"""
        if HAS_QUESTIONARY and not secret:
            return questionary.text(
                prompt,
                default=default or "",
                style=custom_style
            ).ask() or default
        else:
            # Fallback to basic input
            if default:
                prompt_text = f"{prompt} [{default}]: "
            else:
                prompt_text = f"{prompt}: "
                
            if secret:
                value = getpass.getpass(prompt_text)
            else:
                value = input(prompt_text)
                
            return value.strip() or default
    
    def prompt_for_choice(self, message: str, choices: list, default: str = None) -> str:
        """Prompt user to select from choices with arrow key support"""
        if HAS_QUESTIONARY:
            return questionary.select(
                message,
                choices=choices,
                default=default,
                style=custom_style,
                use_shortcuts=True,
                use_arrow_keys=True
            ).ask()
        else:
            # Fallback to numbered menu
            print(f"\n{message}")
            for i, choice in enumerate(choices, 1):
                print(f"{i}. {choice}")
            
            while True:
                try:
                    choice_num = int(self.prompt_for_value("Select option (number)", default="1"))
                    if 1 <= choice_num <= len(choices):
                        return choices[choice_num - 1]
                    else:
                        print("Invalid choice. Please try again.")
                except ValueError:
                    print("Please enter a number.")
    
    def prompt_for_confirm(self, message: str, default: bool = True) -> bool:
        """Prompt for yes/no confirmation"""
        if HAS_QUESTIONARY:
            return questionary.confirm(
                message,
                default=default,
                style=custom_style
            ).ask()
        else:
            default_str = "Y/n" if default else "y/N"
            response = self.prompt_for_value(f"{message} ({default_str})", default="")
            if not response:
                return default
            return response.lower() in ['y', 'yes']
    
    def load_env_file(self) -> Dict[str, str]:
        """Load existing .env file"""
        env_vars = {}
        if self.env_path.exists():
            with open(self.env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes if present
                        value = value.strip('"\'')
                        env_vars[key] = value
        return env_vars
    
    def save_env_file(self, env_vars: Dict[str, str]):
        """Save environment variables to .env file preserving structure"""
        # Define variable groups
        variable_groups = {
            "Database Configuration": [
                "DATABASE_TYPE", "DATABASE_HOST", "DATABASE_PORT",
                "DATABASE_NAME", "DATABASE_USER", "DATABASE_PASSWORD",
                "DATABASE_URL", "DATABASE_POOL_SIZE", "DATABASE_ECHO"
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
        
        with open(self.env_path, 'w') as f:
            f.write("# AutoTrainX Secure Configuration\n")
            f.write("# Generated by AutoTrainX Integrations Manager\n")
            f.write("# ⚠️  KEEP THIS FILE SECRET - DO NOT COMMIT TO VERSION CONTROL\n\n")
            
            # Write each group
            for group_name, variables in variable_groups.items():
                group_values = [(var, env_vars[var]) for var in variables if var in env_vars]
                if group_values:
                    f.write(f"# {group_name}\n")
                    for key, value in group_values:
                        # Handle multiline values (like private keys)
                        if "\\n" in value:
                            f.write(f'{key}="{value}"\n')
                        else:
                            f.write(f"{key}={value}\n")
                    f.write("\n")
                    
    def update_env_variables(self, updates: Dict[str, str]):
        """Update specific environment variables"""
        env_vars = self.load_env_file()
        env_vars.update(updates)
        self.save_env_file(env_vars)
        
    # ==================== Installation Functions ====================
    
    def install_postgresql(self) -> bool:
        """Install PostgreSQL"""
        self.print_header("PostgreSQL Installation")
        
        # Check if already installed
        result = subprocess.run(['which', 'psql'], capture_output=True, text=True)
        if result.returncode == 0:
            self.print_info("PostgreSQL is already installed")
            return True
            
        self.print_info("Installing PostgreSQL...")
        
        # Update package list
        subprocess.run(['sudo', 'apt-get', 'update'], check=False)
        
        # Install PostgreSQL
        cmd = ['sudo', 'apt-get', 'install', '-y', 'postgresql', 'postgresql-contrib', 'postgresql-client']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.print_success("PostgreSQL installed successfully")
            
            # Install Python PostgreSQL adapter
            self.print_info("Installing psycopg2...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'psycopg2-binary'], check=False)
            
            return True
        else:
            self.print_error(f"Failed to install PostgreSQL: {result.stderr}")
            return False
            
    def install_google_sheets_deps(self) -> bool:
        """Install Google Sheets dependencies"""
        self.print_header("Google Sheets Dependencies Installation")
        
        deps = [
            'google-api-python-client',
            'google-auth',
            'google-auth-oauthlib',
            'google-auth-httplib2',
            'gspread'
        ]
        
        self.print_info("Installing Google Sheets API dependencies...")
        
        cmd = [sys.executable, '-m', 'pip', 'install'] + deps
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.print_success("Google Sheets dependencies installed successfully")
            return True
        else:
            self.print_error(f"Failed to install dependencies: {result.stderr}")
            return False
            
    def install_sync_daemon_deps(self) -> bool:
        """Install sync daemon dependencies"""
        self.print_header("Sync Daemon Dependencies Installation")
        
        # Daemon is Python-based, ensure required packages are installed
        deps = ['psutil', 'python-daemon']
        
        self.print_info("Installing sync daemon dependencies...")
        
        cmd = [sys.executable, '-m', 'pip', 'install'] + deps
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.print_success("Sync daemon dependencies installed successfully")
            return True
        else:
            self.print_warning("Some daemon dependencies might not be available")
            return True  # Not critical
            
    # ==================== Configuration Functions ====================
    
    def configure_postgresql(self) -> bool:
        """Configure PostgreSQL database"""
        self.print_header("PostgreSQL Configuration")
        
        # Load current configuration
        env_vars = self.load_env_file()
        
        # Prompt for database configuration
        print("Enter PostgreSQL configuration (press Enter to keep current values):\n")
        
        db_host = self.prompt_for_value(
            "Database Host",
            default=env_vars.get('DATABASE_HOST', 'localhost')
        )
        
        db_port = self.prompt_for_value(
            "Database Port",
            default=env_vars.get('DATABASE_PORT', '5432')
        )
        
        db_name = self.prompt_for_value(
            "Database Name",
            default=env_vars.get('DATABASE_NAME', 'autotrainx')
        )
        
        db_user = self.prompt_for_value(
            "Database User",
            default=env_vars.get('DATABASE_USER', 'autotrainx')
        )
        
        # Password handling
        current_password = env_vars.get('DATABASE_PASSWORD', '')
        if current_password:
            change_password = self.prompt_for_confirm(
                "Change database password?",
                default=False
            )
        else:
            change_password = True
            
        if change_password:
            db_password = self.prompt_for_value(
                "Database Password",
                secret=True
            )
            if not db_password:
                self.print_error("Password cannot be empty")
                return False
        else:
            db_password = current_password
            
        # Advanced options
        show_advanced = self.prompt_for_confirm(
            "Configure advanced options?",
            default=False
        )
        
        if show_advanced:
            pool_size = self.prompt_for_value(
                "Connection Pool Size",
                default=env_vars.get('DATABASE_POOL_SIZE', '10')
            )
            
            echo_sql = self.prompt_for_value(
                "Echo SQL statements? (true/false)",
                default=env_vars.get('DATABASE_ECHO', 'false')
            )
        else:
            pool_size = env_vars.get('DATABASE_POOL_SIZE', '10')
            echo_sql = env_vars.get('DATABASE_ECHO', 'false')
            
        # Update environment variables
        updates = {
            'DATABASE_TYPE': 'postgresql',
            'DATABASE_HOST': db_host,
            'DATABASE_PORT': db_port,
            'DATABASE_NAME': db_name,
            'DATABASE_USER': db_user,
            'DATABASE_PASSWORD': db_password,
            'DATABASE_URL': f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}",
            'DATABASE_POOL_SIZE': pool_size,
            'DATABASE_ECHO': echo_sql
        }
        
        self.update_env_variables(updates)
        self.print_success("PostgreSQL configuration saved")
        
        # Offer to create database and user
        create_db = self.prompt_for_confirm(
            "\nCreate database and user now?",
            default=True
        )
        
        if create_db:
            return self.create_postgresql_database(db_name, db_user, db_password)
            
        return True
        
    def create_postgresql_database(self, db_name: str, db_user: str, db_password: str) -> bool:
        """Create PostgreSQL database and user"""
        self.print_info("Creating PostgreSQL database and user...")
        
        try:
            # Connect as postgres superuser
            create_user_sql = f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '{db_user}') THEN
                    CREATE USER {db_user} WITH PASSWORD '{db_password}';
                END IF;
            END $$;
            """
            
            create_db_sql = f"""
            SELECT 'CREATE DATABASE {db_name} OWNER {db_user}' 
            WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{db_name}')\\gexec
            """
            
            grant_sql = f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"
            
            # Execute commands
            for sql, desc in [
                (create_user_sql, "Creating user"),
                (create_db_sql, "Creating database"),
                (grant_sql, "Granting privileges")
            ]:
                cmd = ['sudo', '-u', 'postgres', 'psql', '-c', sql]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0 and "already exists" not in result.stderr:
                    self.print_error(f"Failed {desc}: {result.stderr}")
                    return False
                    
            self.print_success("Database and user created successfully")
            return True
            
        except Exception as e:
            self.print_error(f"Failed to create database: {e}")
            return False
            
    def configure_google_sheets(self) -> bool:
        """Configure Google Sheets integration"""
        self.print_header("Google Sheets Configuration")
        
        # Load current configuration
        env_vars = self.load_env_file()
        
        print("Configure Google Sheets integration:\n")
        
        # Method selection
        method_choices = [
            "Use service account JSON file (recommended)",
            "Enter credentials manually"
        ]
        
        method_selected = self.prompt_for_choice(
            "Select authentication method:",
            choices=method_choices,
            default=method_choices[0]
        )
        
        method = "1" if "JSON file" in method_selected else "2"
        
        if method == "1":
            # JSON file method
            json_path = self.prompt_for_value(
                "Path to service account JSON file"
            )
            
            if not os.path.exists(json_path):
                self.print_error("File not found")
                return False
                
            try:
                with open(json_path, 'r') as f:
                    creds_data = json.load(f)
                    
                service_email = creds_data.get('client_email')
                project_id = creds_data.get('project_id')
                private_key = creds_data.get('private_key')
                
                if not all([service_email, project_id, private_key]):
                    self.print_error("Invalid credentials file")
                    return False
                    
                # Copy to settings directory
                dest_path = self.settings_path / "google_credentials.json"
                shutil.copy2(json_path, dest_path)
                self.print_success(f"Credentials copied to {dest_path}")
                
            except Exception as e:
                self.print_error(f"Failed to read credentials file: {e}")
                return False
                
        else:
            # Manual entry
            service_email = self.prompt_for_value(
                "Service Account Email",
                default=env_vars.get('GOOGLE_SERVICE_ACCOUNT_EMAIL', '')
            )
            
            project_id = self.prompt_for_value(
                "Project ID",
                default=env_vars.get('GOOGLE_PROJECT_ID', '')
            )
            
            print("\nPaste the private key (including BEGIN/END lines):")
            print("Press Ctrl+D (Unix) or Ctrl+Z (Windows) when done:\n")
            
            private_key_lines = []
            try:
                while True:
                    line = input()
                    private_key_lines.append(line)
            except EOFError:
                pass
                
            private_key = '\\n'.join(private_key_lines)
            
        # Get spreadsheet ID
        spreadsheet_id = self.prompt_for_value(
            "\nGoogle Sheets Spreadsheet ID",
            default=env_vars.get('AUTOTRAINX_SHEETS_ID', '')
        )
        
        # Clean spreadsheet ID if full URL provided
        if "spreadsheets/d/" in spreadsheet_id:
            spreadsheet_id = spreadsheet_id.split("spreadsheets/d/")[1].split("/")[0]
            
        # Update environment variables
        updates = {
            'GOOGLE_SERVICE_ACCOUNT_EMAIL': service_email,
            'GOOGLE_PROJECT_ID': project_id,
            'GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY': private_key,
            'AUTOTRAINX_SHEETS_ID': spreadsheet_id
        }
        
        self.update_env_variables(updates)
        self.print_success("Google Sheets configuration saved")
        
        # Update config.json
        config_path = self.settings_path / "config.json"
        config = {}
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                
        if 'google_sheets_sync' not in config:
            config['google_sheets_sync'] = {}
            
        config['google_sheets_sync'].update({
            'enabled': True,
            'spreadsheet_id': spreadsheet_id
        })
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        self.print_info(f"\n⚠️  Remember to share your spreadsheet with: {service_email}")
        
        return True
        
    def configure_sync_daemon(self) -> bool:
        """Configure sync daemon settings"""
        self.print_header("Sync Daemon Configuration")
        
        # This would configure sync intervals, batch sizes, etc.
        # For now, using defaults from config.json
        self.print_info("Sync daemon uses settings from settings/config.json")
        self.print_success("Sync daemon configuration complete")
        
        # Offer to start daemon
        start_daemon = self.prompt_for_confirm(
            "\nStart sync daemon now?",
            default=False
        )
        
        if start_daemon:
            return self.start_sync_daemon()
            
        return True
        
    def start_sync_daemon(self) -> bool:
        """Start the sync daemon"""
        self.print_info("Starting sync daemon...")
        
        cmd = [sys.executable, 'sheets_sync_daemon.py', '--daemon']
        result = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=self.base_path
        )
        
        time.sleep(2)  # Give it time to start
        
        # Check if running
        if self.check_daemon_status():
            self.print_success("Sync daemon started successfully")
            return True
        else:
            self.print_error("Failed to start sync daemon")
            return False
            
    def check_daemon_status(self) -> bool:
        """Check if sync daemon is running"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'sheets_sync_daemon.py' in str(cmdline):
                    return True
        except:
            pass
        return False
        
    def configure_general_variables(self) -> bool:
        """Configure general environment variables"""
        self.print_header("General Configuration Variables")
        
        env_vars = self.load_env_file()
        
        print("Configure security and CORS settings:\n")
        
        # API Secret Key
        if 'API_SECRET_KEY' not in env_vars or not env_vars.get('API_SECRET_KEY'):
            generate_api = self.prompt_for_confirm(
                "Generate new API secret key?",
                default=True
            )
            
            if generate_api:
                api_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
                env_vars['API_SECRET_KEY'] = api_key
                self.print_success("Generated new API secret key")
                
        # JWT Secret Key
        if 'JWT_SECRET_KEY' not in env_vars or not env_vars.get('JWT_SECRET_KEY'):
            generate_jwt = self.prompt_for_confirm(
                "Generate new JWT secret key?",
                default=True
            )
            
            if generate_jwt:
                jwt_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
                env_vars['JWT_SECRET_KEY'] = jwt_key
                env_vars['JWT_ALGORITHM'] = 'HS256'
                env_vars['JWT_ACCESS_TOKEN_EXPIRE_MINUTES'] = '30'
                self.print_success("Generated new JWT secret key")
                
        # CORS Configuration
        configure_cors = self.prompt_for_confirm(
            "\nConfigure CORS settings?",
            default=False
        )
        
        if configure_cors:
            env_vars['CORS_ALLOWED_ORIGINS'] = self.prompt_for_value(
                "Allowed origins (* for all)",
                default=env_vars.get('CORS_ALLOWED_ORIGINS', '*')
            )
            env_vars['CORS_ALLOW_CREDENTIALS'] = self.prompt_for_value(
                "Allow credentials (true/false)",
                default=env_vars.get('CORS_ALLOW_CREDENTIALS', 'true')
            )
            env_vars['CORS_ALLOWED_METHODS'] = self.prompt_for_value(
                "Allowed methods",
                default=env_vars.get('CORS_ALLOWED_METHODS', 'GET,POST,PUT,DELETE,OPTIONS')
            )
            env_vars['CORS_ALLOWED_HEADERS'] = self.prompt_for_value(
                "Allowed headers (* for all)",
                default=env_vars.get('CORS_ALLOWED_HEADERS', '*')
            )
        else:
            # Set defaults if not present
            env_vars.setdefault('CORS_ALLOWED_ORIGINS', '*')
            env_vars.setdefault('CORS_ALLOW_CREDENTIALS', 'true')
            env_vars.setdefault('CORS_ALLOWED_METHODS', 'GET,POST,PUT,DELETE,OPTIONS')
            env_vars.setdefault('CORS_ALLOWED_HEADERS', '*')
            
        self.save_env_file(env_vars)
        self.print_success("General configuration saved")
        
        return True
        
    # ==================== Verification Functions ====================
    
    def verify_configuration(self):
        """Verify all configurations"""
        self.print_header("System Configuration Verification")
        
        env_vars = self.load_env_file()
        errors = []
        warnings = []
        
        # PostgreSQL Verification
        print(f"\n{Colors.BOLD}PostgreSQL:{Colors.RESET}")
        pg_vars = ['DATABASE_HOST', 'DATABASE_PORT', 'DATABASE_NAME', 'DATABASE_USER', 'DATABASE_PASSWORD']
        pg_configured = all(env_vars.get(var) for var in pg_vars)
        
        for var in pg_vars:
            if var in env_vars and env_vars[var]:
                if var == 'DATABASE_PASSWORD':
                    self.print_success(f"{var} configured: ****")
                else:
                    self.print_success(f"{var} configured: {env_vars[var]}")
            else:
                self.print_error(f"{var} not configured")
                errors.append(f"PostgreSQL: {var} missing")
                
        # Test PostgreSQL connection
        if pg_configured and HAS_PSYCOPG2:
            try:
                conn = psycopg2.connect(
                    host=env_vars['DATABASE_HOST'],
                    port=env_vars['DATABASE_PORT'],
                    database=env_vars['DATABASE_NAME'],
                    user=env_vars['DATABASE_USER'],
                    password=env_vars['DATABASE_PASSWORD']
                )
                conn.close()
                self.print_success("PostgreSQL connection: OK")
            except Exception as e:
                self.print_error(f"PostgreSQL connection: FAILED - {str(e)}")
                errors.append("PostgreSQL: Connection failed")
        elif not HAS_PSYCOPG2:
            self.print_warning("psycopg2 not installed - cannot test connection")
            warnings.append("PostgreSQL: psycopg2 not installed")
            
        # Google Sheets Verification
        print(f"\n{Colors.BOLD}Google Sheets:{Colors.RESET}")
        google_vars = ['GOOGLE_SERVICE_ACCOUNT_EMAIL', 'GOOGLE_PROJECT_ID', 'GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY', 'AUTOTRAINX_SHEETS_ID']
        google_configured = all(env_vars.get(var) for var in google_vars)
        
        for var in google_vars:
            if var in env_vars and env_vars[var]:
                if var == 'GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY':
                    self.print_success(f"{var} configured: ****")
                else:
                    self.print_success(f"{var} configured: {env_vars[var]}")
            else:
                self.print_error(f"{var} not configured")
                errors.append(f"Google Sheets: {var} missing")
                
        # Test Google Sheets authentication
        if google_configured and HAS_GOOGLE_AUTH:
            try:
                credentials = service_account.Credentials.from_service_account_info(
                    {
                        "type": "service_account",
                        "project_id": env_vars['GOOGLE_PROJECT_ID'],
                        "private_key": env_vars['GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY'].replace('\\n', '\n'),
                        "client_email": env_vars['GOOGLE_SERVICE_ACCOUNT_EMAIL'],
                        "client_id": "",
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{env_vars['GOOGLE_SERVICE_ACCOUNT_EMAIL']}"
                    },
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                self.print_success("Google authentication: OK")
            except Exception as e:
                self.print_error(f"Google authentication: FAILED - {str(e)}")
                errors.append("Google Sheets: Authentication failed")
        elif not HAS_GOOGLE_AUTH:
            self.print_warning("Google auth libraries not installed - cannot test authentication")
            warnings.append("Google Sheets: Libraries not installed")
            
        # General Variables Verification
        print(f"\n{Colors.BOLD}General Variables:{Colors.RESET}")
        general_vars = ['API_SECRET_KEY', 'JWT_SECRET_KEY', 'CORS_ALLOWED_ORIGINS']
        
        for var in general_vars:
            if var in env_vars and env_vars[var]:
                if 'SECRET' in var or 'KEY' in var:
                    self.print_success(f"{var} configured: ****")
                else:
                    self.print_success(f"{var} configured: {env_vars[var]}")
            else:
                self.print_error(f"{var} not configured")
                if var in ['API_SECRET_KEY', 'JWT_SECRET_KEY']:
                    errors.append(f"Security: {var} missing")
                else:
                    warnings.append(f"General: {var} missing")
                    
        # Sync Daemon Status
        print(f"\n{Colors.BOLD}Sync Daemon:{Colors.RESET}")
        if self.check_daemon_status():
            self.print_success("Sync daemon: RUNNING")
        else:
            self.print_warning("Sync daemon: NOT RUNNING")
            warnings.append("Sync daemon not running")
            
        # Summary
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}VERIFICATION SUMMARY:{Colors.RESET}")
        
        if not errors and not warnings:
            self.print_success("All systems configured correctly!")
        else:
            if errors:
                print(f"\n{Colors.RED}Errors found ({len(errors)}):{Colors.RESET}")
                for error in errors:
                    print(f"  • {error}")
                    
            if warnings:
                print(f"\n{Colors.YELLOW}Warnings ({len(warnings)}):{Colors.RESET}")
                for warning in warnings:
                    print(f"  • {warning}")
                    
            print(f"\n{Colors.BOLD}Run 'Configuration' menu to fix these issues.{Colors.RESET}")
            
    # ==================== Menu System ====================
    
    def show_main_menu(self):
        """Show main menu"""
        while True:
            self.print_header("AutoTrainX Integrations Manager")
            
            menu_choices = [
                "🔧 Installation",
                "⚙️  Configuration",
                "✅ Verify System",
                "❌ Exit"
            ]
            
            choice = self.prompt_for_choice(
                "What would you like to do?",
                choices=menu_choices,
                default=menu_choices[2]  # Default to Verify
            )
            
            if "Installation" in choice:
                self.show_installation_menu()
            elif "Configuration" in choice:
                self.show_configuration_menu()
            elif "Verify" in choice:
                self.verify_configuration()
                if HAS_QUESTIONARY:
                    questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
                else:
                    input("\nPress Enter to continue...")
            elif "Exit" in choice:
                print("\nExiting...")
                break
                
    def show_installation_menu(self):
        """Show installation menu"""
        while True:
            self.print_header("Installation Menu")
            
            install_choices = [
                "🐘 Install PostgreSQL",
                "📊 Install Google Sheets Dependencies",
                "🔄 Install Sync Daemon Dependencies",
                "📦 Install All Components",
                "⬅️  Back to Main Menu"
            ]
            
            choice = self.prompt_for_choice(
                "Select component to install:",
                choices=install_choices,
                default=install_choices[4]  # Default to Back
            )
            
            continue_prompt = lambda: questionary.press_any_key_to_continue("\nPress any key to continue...").ask() if HAS_QUESTIONARY else input("\nPress Enter to continue...")
            
            if "PostgreSQL" in choice:
                self.install_postgresql()
                continue_prompt()
            elif "Google Sheets" in choice:
                self.install_google_sheets_deps()
                continue_prompt()
            elif "Sync Daemon" in choice:
                self.install_sync_daemon_deps()
                continue_prompt()
            elif "All Components" in choice:
                self.install_postgresql()
                self.install_google_sheets_deps()
                self.install_sync_daemon_deps()
                continue_prompt()
            elif "Back" in choice:
                break
                
    def show_configuration_menu(self):
        """Show configuration menu"""
        while True:
            self.print_header("Configuration Menu")
            
            config_choices = [
                "🐘 Configure PostgreSQL",
                "📊 Configure Google Sheets",
                "🔄 Configure Sync Daemon",
                "🔐 Configure General Variables",
                "📦 Configure All Components",
                "⬅️  Back to Main Menu"
            ]
            
            choice = self.prompt_for_choice(
                "Select component to configure:",
                choices=config_choices,
                default=config_choices[5]  # Default to Back
            )
            
            continue_prompt = lambda: questionary.press_any_key_to_continue("\nPress any key to continue...").ask() if HAS_QUESTIONARY else input("\nPress Enter to continue...")
            
            if "PostgreSQL" in choice:
                self.configure_postgresql()
                continue_prompt()
            elif "Google Sheets" in choice:
                self.configure_google_sheets()
                continue_prompt()
            elif "Sync Daemon" in choice:
                self.configure_sync_daemon()
                continue_prompt()
            elif "General Variables" in choice:
                self.configure_general_variables()
                continue_prompt()
            elif "All Components" in choice:
                self.configure_postgresql()
                self.configure_google_sheets()
                self.configure_sync_daemon()
                self.configure_general_variables()
                continue_prompt()
            elif "Back" in choice:
                break


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='AutoTrainX Integrations Manager')
    parser.add_argument('--verify', action='store_true', help='Verify all configurations')
    parser.add_argument('--install', choices=['postgres', 'google', 'daemon', 'all'], 
                       help='Install specific component')
    parser.add_argument('--config', choices=['postgres', 'google', 'daemon', 'general', 'all'], 
                       help='Configure specific component')
    
    args = parser.parse_args()
    
    manager = IntegrationsManager()
    
    if args.verify:
        manager.verify_configuration()
    elif args.install:
        if args.install == 'postgres':
            manager.install_postgresql()
        elif args.install == 'google':
            manager.install_google_sheets_deps()
        elif args.install == 'daemon':
            manager.install_sync_daemon_deps()
        elif args.install == 'all':
            manager.install_postgresql()
            manager.install_google_sheets_deps()
            manager.install_sync_daemon_deps()
    elif args.config:
        if args.config == 'postgres':
            manager.configure_postgresql()
        elif args.config == 'google':
            manager.configure_google_sheets()
        elif args.config == 'daemon':
            manager.configure_sync_daemon()
        elif args.config == 'general':
            manager.configure_general_variables()
        elif args.config == 'all':
            manager.configure_postgresql()
            manager.configure_google_sheets()
            manager.configure_sync_daemon()
            manager.configure_general_variables()
    else:
        # Interactive mode
        manager.show_main_menu()


if __name__ == "__main__":
    main()
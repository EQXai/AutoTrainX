#!/usr/bin/env python3
"""
AutoTrainX Unified Setup Script

This script combines the functionality of:
- setup_secure_config.py (secure .env configuration)
- setup_postgresql.sh (PostgreSQL installation and setup)
- setup_google_sheets.py (Google Sheets integration)
- sheets_sync_daemon.py (daemon management)

It ensures proper execution order and prevents conflicts with setup.sh.

Usage:
    python unified_setup.py                    # Interactive setup
    python unified_setup.py --check-only       # Check current configuration
    python unified_setup.py --fix-conflicts    # Fix conflicts with setup.sh
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
import psutil

# Try to import terminal control modules (Unix-like systems)
try:
    import termios
    import tty
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False


class Colors:
    """Terminal color codes"""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color


class UnifiedSetup:
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.env_path = self.root_dir / ".env"
        self.settings_dir = self.root_dir / "settings"
        self.config_json_path = self.settings_dir / "config.json"
        self.setup_config_path = self.root_dir / ".setup_config.json"
        self.daemon_pid_file = self.root_dir / ".sheets_sync_daemon.pid"
        
        # Check if running in Docker or as root
        self.is_docker = os.path.exists('/.dockerenv')
        self.is_root = os.geteuid() == 0
        
        # Track what needs to be configured
        self.needs_env_config = False
        self.needs_postgresql = False
        self.needs_google_sheets = False
        self.has_conflicts = False
        
        # Configuration data
        self.config = {}
        
    def print_header(self, message: str):
        """Print a formatted header"""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 80}{Colors.NC}")
        print(f"{Colors.CYAN}{Colors.BOLD}  {message}{Colors.NC}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 80}{Colors.NC}\n")
        
    def print_info(self, message: str):
        """Print an info message"""
        print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")
        
    def print_success(self, message: str):
        """Print a success message"""
        print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")
        
    def print_warning(self, message: str):
        """Print a warning message"""
        print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")
        
    def print_error(self, message: str):
        """Print an error message"""
        print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")
        
    def print_step(self, step: int, total: int, message: str):
        """Print a step indicator"""
        print(f"\n{Colors.MAGENTA}[STEP {step}/{total}]{Colors.NC} {message}")
        
    def prompt_for_value(self, prompt: str, default: Optional[str] = None, is_password: bool = False) -> str:
        """Prompt user for a value with optional default"""
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
        
    def generate_secure_password(self, length: int = 32) -> str:
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
        
    def generate_secret_key(self) -> str:
        """Generate a secure secret key for API/JWT"""
        return secrets.token_hex(32)
        
    def check_current_state(self) -> Dict[str, Any]:
        """Check the current state of the installation"""
        state = {
            "env_exists": self.env_path.exists(),
            "settings_exists": self.settings_dir.exists(),
            "config_json_exists": self.config_json_path.exists(),
            "setup_config_exists": self.setup_config_path.exists(),
            "postgresql_installed": self.check_postgresql_installed(),
            "postgresql_running": self.check_postgresql_running(),
            "postgresql_connection_ok": False,
            "google_sheets_configured": self.check_google_sheets_configured(),
            "google_sheets_connection_ok": False,
            "daemon_running": self.check_daemon_running(),
            "daemon_healthy": False,
            "conflicts": []
        }
        
        # Test PostgreSQL connection if it's running
        if state["postgresql_running"]:
            state["postgresql_connection_ok"] = self.test_postgresql_connection()
            
        # Test Google Sheets connection if configured
        if state["google_sheets_configured"]:
            state["google_sheets_connection_ok"] = self.test_google_sheets_connection()
            
        # Check daemon health if running
        if state["daemon_running"]:
            state["daemon_healthy"] = self.test_daemon_health()
        
        # Check for conflicts with setup.sh
        if self.setup_config_path.exists():
            try:
                with open(self.setup_config_path, 'r') as f:
                    setup_config = json.load(f)
                    
                # Check if setup.sh was configured to install PostgreSQL
                if setup_config.get("components", {}).get("postgresql", False):
                    state["conflicts"].append("setup.sh configured to install PostgreSQL")
                    
                # Check if setup.sh was configured to install Google Sheets
                if setup_config.get("components", {}).get("google_sheets", False):
                    state["conflicts"].append("setup.sh configured to install Google Sheets")
                    
            except Exception as e:
                self.print_warning(f"Could not read setup.sh config: {e}")
                
        return state
        
    def check_postgresql_installed(self) -> bool:
        """Check if PostgreSQL is installed"""
        try:
            result = subprocess.run(['which', 'psql'], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
            
    def check_postgresql_running(self) -> bool:
        """Check if PostgreSQL is running"""
        try:
            # Method 1: Check if postgres process is running
            ps_result = subprocess.run(['pgrep', '-f', 'postgres'], capture_output=True, text=True)
            if ps_result.returncode != 0:
                return False
                
            # Method 2: Try to connect
            if self.is_root or self.is_docker:
                # Direct connection as postgres user without sudo
                result = subprocess.run(
                    ['su', '-', 'postgres', '-c', 'psql -c "SELECT 1;" 2>/dev/null'],
                    capture_output=True, text=True
                )
            else:
                # Use sudo for non-root users
                result = subprocess.run(
                    ['sudo', '-u', 'postgres', 'psql', '-c', 'SELECT 1;'],
                    capture_output=True, text=True
                )
            return result.returncode == 0
        except:
            return False
            
    def test_postgresql_connection(self) -> bool:
        """Test PostgreSQL connection with autotrainx user and database"""
        try:
            # Load password from config or .env
            password = self.config.get('DATABASE_PASSWORD')
            if not password:
                password = os.environ.get('DATABASE_PASSWORD')
            if not password and self.env_path.exists():
                with open(self.env_path, 'r') as f:
                    for line in f:
                        if line.startswith('DATABASE_PASSWORD='):
                            password = line.split('=', 1)[1].strip().strip('"').strip("'")
                            break
            
            if not password:
                password = 'AutoTrainX2024Secure123'
                
            # Test connection
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            result = subprocess.run(
                ['psql', '-h', 'localhost', '-U', 'autotrainx', '-d', 'autotrainx', 
                 '-c', 'SELECT current_database(), current_user, version();'],
                env=env,
                capture_output=True,
                text=True
            )
            
            return result.returncode == 0
        except:
            return False
            
    def check_google_sheets_configured(self) -> bool:
        """Check if Google Sheets is configured"""
        if not self.config_json_path.exists():
            return False
            
        try:
            with open(self.config_json_path, 'r') as f:
                config = json.load(f)
                gs_config = config.get('google_sheets_sync', {})
                return gs_config.get('enabled', False) and gs_config.get('spreadsheet_id')
        except:
            return False
            
    def test_google_sheets_connection(self) -> bool:
        """Test Google Sheets API connection"""
        if not self.check_google_sheets_configured():
            return False
            
        try:
            # Try to import Google Sheets client
            import subprocess
            result = subprocess.run([
                sys.executable, '-c',
                """
import json
from pathlib import Path
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    
    # Load config
    config_path = Path('settings/config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    gs_config = config.get('google_sheets_sync', {})
    creds_path = gs_config.get('credentials_path')
    sheet_id = gs_config.get('spreadsheet_id')
    
    # Test connection
    credentials = service_account.Credentials.from_service_account_file(creds_path)
    service = build('sheets', 'v4', credentials=credentials)
    
    # Try to get spreadsheet metadata
    sheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    print("SUCCESS")
except Exception as e:
    print(f"ERROR: {e}")
"""
            ], capture_output=True, text=True)
            
            return "SUCCESS" in result.stdout
        except:
            return False
            
    def check_daemon_running(self) -> bool:
        """Check if sheets sync daemon is running"""
        if not self.daemon_pid_file.exists():
            return False
            
        try:
            pid = int(self.daemon_pid_file.read_text().strip())
            return psutil.Process(pid).is_running()
        except:
            return False
            
    def test_daemon_health(self) -> bool:
        """Test if the daemon is healthy and processing"""
        if not self.check_daemon_running():
            return False
            
        try:
            # Check if daemon log exists and has recent activity
            log_file = self.root_dir / "logs" / "sheets_sync_daemon.log"
            if log_file.exists():
                # Check if log was modified in the last 5 minutes
                import time
                log_mtime = log_file.stat().st_mtime
                current_time = time.time()
                if current_time - log_mtime < 300:  # 5 minutes
                    return True
            
            # Alternative: check if daemon process is responsive
            pid = int(self.daemon_pid_file.read_text().strip())
            process = psutil.Process(pid)
            return process.status() != psutil.STATUS_ZOMBIE
        except:
            return False
            
    def fix_setup_conflicts(self):
        """Fix conflicts with setup.sh configuration"""
        self.print_header("Fixing Setup Conflicts")
        
        if not self.setup_config_path.exists():
            self.print_info("No setup.sh configuration found - no conflicts to fix")
            return
            
        try:
            with open(self.setup_config_path, 'r') as f:
                setup_config = json.load(f)
                
            # Disable PostgreSQL and Google Sheets in setup.sh config
            if "components" in setup_config:
                changed = False
                
                if setup_config["components"].get("postgresql", False):
                    setup_config["components"]["postgresql"] = False
                    changed = True
                    self.print_info("Disabled PostgreSQL in setup.sh config")
                    
                if setup_config["components"].get("google_sheets", False):
                    setup_config["components"]["google_sheets"] = False
                    changed = True
                    self.print_info("Disabled Google Sheets in setup.sh config")
                    
                if changed:
                    with open(self.setup_config_path, 'w') as f:
                        json.dump(setup_config, f, indent=2)
                    self.print_success("Updated setup.sh configuration")
                else:
                    self.print_info("No conflicts found in setup.sh configuration")
                    
        except Exception as e:
            self.print_error(f"Failed to fix setup conflicts: {e}")
            
    def setup_env_configuration(self):
        """Set up secure .env configuration (from setup_secure_config.py)"""
        self.print_step(1, 4, "Configuring Secure Environment (.env)")
        
        # Check if .env already exists
        if self.env_path.exists():
            overwrite = self.prompt_for_value(
                "⚠️  .env file already exists. Overwrite? (y/n)",
                default="n"
            ).lower() == 'y'
            
            if not overwrite:
                self.print_info("Keeping existing .env configuration")
                return
                
        # Database configuration
        print("\n=== Database Configuration ===")
        db_type = self.prompt_for_value(
            "Database type (postgresql/sqlite)",
            default="postgresql"
        ).lower()
        
        self.config["DATABASE_TYPE"] = db_type
        
        if db_type == "postgresql":
            self.config["DATABASE_HOST"] = self.prompt_for_value("Database host", default="localhost")
            self.config["DATABASE_PORT"] = self.prompt_for_value("Database port", default="5432")
            self.config["DATABASE_NAME"] = self.prompt_for_value("Database name", default="autotrainx")
            self.config["DATABASE_USER"] = self.prompt_for_value("Database user", default="autotrainx")
            
            use_generated = self.prompt_for_value(
                "Generate secure password? (y/n)",
                default="y"
            ).lower() == 'y'
            
            if use_generated:
                password = self.generate_secure_password()
                print(f"Generated password: {password}")
                print("⚠️  IMPORTANT: Save this password securely!")
            else:
                password = self.prompt_for_value("Database password", is_password=True)
                
            self.config["DATABASE_PASSWORD"] = password
            self.config["DATABASE_URL"] = f"postgresql://{self.config['DATABASE_USER']}:{password}@{self.config['DATABASE_HOST']}:{self.config['DATABASE_PORT']}/{self.config['DATABASE_NAME']}"
        else:
            db_path = self.prompt_for_value("SQLite database path", default="./DB/autotrainx.db")
            self.config["DATABASE_URL"] = f"sqlite:///{db_path}"
            
        # Security configuration
        print("\n=== Security Configuration ===")
        generate_api_key = self.prompt_for_value(
            "Generate secure API secret key? (y/n)",
            default="y"
        ).lower() == 'y'
        
        if generate_api_key:
            api_key = self.generate_secret_key()
            self.config["API_SECRET_KEY"] = api_key
        else:
            self.config["API_SECRET_KEY"] = self.prompt_for_value("API secret key")
            
        # JWT configuration
        generate_jwt_key = self.prompt_for_value(
            "Generate secure JWT secret key? (y/n)",
            default="y"
        ).lower() == 'y'
        
        if generate_jwt_key:
            jwt_key = self.generate_secret_key()
            self.config["JWT_SECRET_KEY"] = jwt_key
        else:
            self.config["JWT_SECRET_KEY"] = self.prompt_for_value("JWT secret key")
            
        self.config["JWT_ALGORITHM"] = "HS256"
        self.config["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = self.prompt_for_value(
            "JWT token expiration (minutes)",
            default="30"
        )
        
        # CORS configuration
        print("\n=== CORS Configuration ===")
        is_production = self.prompt_for_value(
            "Is this for production? (y/n)",
            default="n"
        ).lower() == 'y'
        
        if is_production:
            origins = self.prompt_for_value("Allowed origins (comma-separated)")
            self.config["CORS_ALLOWED_ORIGINS"] = origins
        else:
            self.config["CORS_ALLOWED_ORIGINS"] = "*"
            
        # Write .env file
        self.write_env_file()
        self.print_success(".env configuration completed")
        
    def write_env_file(self):
        """Write configuration to .env file"""
        with open(self.env_path, 'w') as f:
            f.write("# AutoTrainX Secure Configuration\n")
            f.write("# Generated by unified_setup.py\n")
            f.write("# ⚠️  KEEP THIS FILE SECRET - DO NOT COMMIT TO VERSION CONTROL\n\n")
            
            # Database configuration
            if "DATABASE_TYPE" in self.config:
                f.write("# Database Configuration\n")
                for key in ["DATABASE_TYPE", "DATABASE_URL", "DATABASE_HOST", "DATABASE_PORT",
                           "DATABASE_NAME", "DATABASE_USER", "DATABASE_PASSWORD"]:
                    if key in self.config:
                        f.write(f"{key}={self.config[key]}\n")
                f.write("\n")
                
            # Security configuration
            f.write("# Security Configuration\n")
            for key in ["API_SECRET_KEY", "JWT_SECRET_KEY", "JWT_ALGORITHM",
                       "JWT_ACCESS_TOKEN_EXPIRE_MINUTES"]:
                if key in self.config:
                    f.write(f"{key}={self.config[key]}\n")
            f.write("\n")
            
            # CORS configuration
            f.write("# CORS Configuration\n")
            f.write(f"CORS_ALLOWED_ORIGINS={self.config.get('CORS_ALLOWED_ORIGINS', '*')}\n")
            f.write("CORS_ALLOW_CREDENTIALS=true\n")
            f.write("CORS_ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS\n")
            f.write("CORS_ALLOWED_HEADERS=*\n\n")
            
                
    def run_privileged_command(self, command: list) -> subprocess.CompletedProcess:
        """Run a command with appropriate privileges"""
        if self.is_root or self.is_docker:
            # Already root or in Docker, run directly
            return subprocess.run(command, capture_output=True, text=True)
        else:
            # Use sudo for non-root users
            return subprocess.run(['sudo'] + command, capture_output=True, text=True)
    
    def configure_postgresql_docker_auth(self):
        """Configure PostgreSQL authentication for Docker environment"""
        try:
            # Find PostgreSQL version
            pg_versions = subprocess.run(['ls', '/etc/postgresql/'], capture_output=True, text=True)
            if pg_versions.returncode == 0 and pg_versions.stdout.strip():
                version = pg_versions.stdout.strip().split()[0]
                hba_file = f"/etc/postgresql/{version}/main/pg_hba.conf"
                
                if os.path.exists(hba_file):
                    # Backup original
                    subprocess.run(['cp', hba_file, f"{hba_file}.backup"], check=False)
                    
                    # Write trust authentication config
                    hba_content = """# PostgreSQL Client Authentication Configuration
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Allow local connections without password (Docker environment)
local   all             postgres                                trust
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust

# Allow connections from Docker network
host    all             all             172.16.0.0/12           trust
host    all             all             192.168.0.0/16          trust
"""
                    with open(hba_file, 'w') as f:
                        f.write(hba_content)
                    
                    self.print_info("PostgreSQL authentication configured for Docker")
        except Exception as e:
            self.print_warning(f"Could not configure PostgreSQL auth: {e}")
    
    def setup_postgresql(self):
        """Set up PostgreSQL (from setup_postgresql.sh)"""
        self.print_step(2, 4, "Setting up PostgreSQL Database")
        
        # Check if PostgreSQL is already installed
        if not self.check_postgresql_installed():
            install = self.prompt_for_value(
                "PostgreSQL is not installed. Install now? (y/n)",
                default="y"
            ).lower() == 'y'
            
            if install:
                self.print_info("Installing PostgreSQL...")
                try:
                    self.run_privileged_command(['apt-get', 'update'])
                    self.run_privileged_command(['apt-get', 'install', '-y', 
                                               'postgresql', 'postgresql-client', 'postgresql-contrib'])
                    self.print_success("PostgreSQL installed successfully")
                except subprocess.CalledProcessError as e:
                    self.print_error(f"Failed to install PostgreSQL: {e}")
                    return False
            else:
                self.print_warning("PostgreSQL installation skipped")
                return False
                
        # Start PostgreSQL if not running
        if not self.check_postgresql_running():
            self.print_info("Starting PostgreSQL service...")
            try:
                # Try different methods to start PostgreSQL
                if self.is_docker:
                    self.print_info("Starting PostgreSQL in Docker environment...")
                    
                    # Create necessary directories
                    os.makedirs('/var/run/postgresql', exist_ok=True)
                    os.makedirs('/var/log/postgresql', exist_ok=True)
                    subprocess.run(['chown', 'postgres:postgres', '/var/run/postgresql'], check=False)
                    subprocess.run(['chown', 'postgres:postgres', '/var/log/postgresql'], check=False)
                    
                    # Method 1: Try using service command first (works in some Docker setups)
                    service_result = subprocess.run(['service', 'postgresql', 'start'], 
                                                  capture_output=True, text=True)
                    if service_result.returncode == 0:
                        self.print_success("PostgreSQL started using service command")
                        time.sleep(3)
                    else:
                        # Method 2: Try to find and use pg_ctl
                        pg_versions = subprocess.run(['ls', '/usr/lib/postgresql/'], 
                                                   capture_output=True, text=True)
                        if pg_versions.returncode == 0 and pg_versions.stdout.strip():
                            version = pg_versions.stdout.strip().split()[0]
                            pg_ctl_path = f"/usr/lib/postgresql/{version}/bin/pg_ctl"
                            data_dir = f"/var/lib/postgresql/{version}/main"
                            
                            if os.path.exists(pg_ctl_path) and os.path.exists(data_dir):
                                # Start PostgreSQL using pg_ctl
                                start_cmd = f"{pg_ctl_path} -D {data_dir} -l /var/log/postgresql/postgresql.log start"
                                subprocess.run(['su', '-', 'postgres', '-c', start_cmd], check=False)
                                self.print_info(f"Started PostgreSQL {version} using pg_ctl")
                                time.sleep(3)
                            else:
                                # Method 3: Try direct postgres command
                                postgres_cmd = f"/usr/lib/postgresql/{version}/bin/postgres"
                                if os.path.exists(postgres_cmd):
                                    # Start in background
                                    subprocess.Popen([
                                        'su', '-', 'postgres', '-c',
                                        f'{postgres_cmd} -D {data_dir}'
                                    ])
                                    self.print_info("Started PostgreSQL using postgres command")
                                    time.sleep(3)
                else:
                    # Use service command for non-Docker
                    self.run_privileged_command(['service', 'postgresql', 'start'])
                    time.sleep(2)
                    
                # Verify PostgreSQL is running
                if not self.check_postgresql_running():
                    self.print_warning("PostgreSQL may not have started properly")
                    self.print_info("Continuing anyway - database operations may fail")
                    
            except Exception as e:
                self.print_warning(f"Could not start PostgreSQL service: {e}")
                self.print_info("Continuing anyway - database operations may fail")
                
        # Get database password from config (which should be loaded from .env)
        db_password = self.config.get('DATABASE_PASSWORD')
        
        # If not in config, try environment variables
        if not db_password:
            db_password = os.environ.get('DATABASE_PASSWORD')
            
        # If still not found, try to read directly from .env file
        if not db_password and self.env_path.exists():
            with open(self.env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('DATABASE_PASSWORD='):
                        db_password = line.split('=', 1)[1].strip().strip('"').strip("'")
                        break
                        
        # Final fallback
        if not db_password:
            db_password = 'AutoTrainX2024Secure123'
            self.print_warning(f"Using default password: {db_password}")
            
        # Configure PostgreSQL authentication for Docker if needed
        if self.is_docker and not self.check_postgresql_running():
            self.print_info("Configuring PostgreSQL for Docker environment...")
            self.configure_postgresql_docker_auth()
            
        # Create database and user
        self.print_info("Creating database and user...")
        sql_commands = f"""
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'autotrainx') THEN
      CREATE USER autotrainx WITH PASSWORD '{db_password}';
   END IF;
END $$;

SELECT 'CREATE DATABASE autotrainx OWNER autotrainx'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'autotrainx')\\gexec

GRANT ALL PRIVILEGES ON DATABASE autotrainx TO autotrainx;
"""
        
        try:
            # Create database and user
            if self.is_root or self.is_docker:
                # Running as root or in Docker
                process = subprocess.Popen(
                    ['su', '-', 'postgres', '-c', 'psql'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            else:
                # Use sudo for non-root users
                process = subprocess.Popen(
                    ['sudo', '-u', 'postgres', 'psql'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            
            stdout, stderr = process.communicate(input=sql_commands)
            
            if process.returncode == 0:
                self.print_success("Database and user created successfully")
            else:
                self.print_error(f"Failed to create database/user: {stderr}")
                return False
                
        except Exception as e:
            self.print_error(f"Failed to setup PostgreSQL: {e}")
            return False
            
        # Test connection
        self.print_info("Testing database connection...")
        try:
            # Ensure we have the correct password
            test_password = db_password
            if not test_password:
                # Try to get from environment or .env file
                test_password = os.environ.get('DATABASE_PASSWORD')
                if not test_password and self.env_path.exists():
                    with open(self.env_path, 'r') as f:
                        for line in f:
                            if line.startswith('DATABASE_PASSWORD='):
                                test_password = line.split('=', 1)[1].strip().strip('"').strip("'")
                                break
                
            if not test_password:
                test_password = 'AutoTrainX2024Secure123'  # Default fallback
                
            env = os.environ.copy()
            env['PGPASSWORD'] = test_password
            result = subprocess.run(
                ['psql', '-h', 'localhost', '-U', 'autotrainx', '-d', 'autotrainx', '-c', 'SELECT 1;'],
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.print_success("Database connection successful!")
                return True
            else:
                self.print_warning("Connection test failed - database was created but authentication may need configuration")
                self.print_info(f"You can test manually with: PGPASSWORD=<your-password> psql -h localhost -U autotrainx -d autotrainx")
                return True  # Still return True as setup completed
                
        except Exception as e:
            self.print_warning(f"Could not test connection: {e}")
            self.print_info("Database was created, you can test the connection manually")
            return True
            
    def setup_google_sheets(self):
        """Set up Google Sheets integration"""
        self.print_step(3, 4, "Setting up Google Sheets Integration")
        
        use_google = self.prompt_for_value(
            "Do you want to configure Google Sheets integration? (y/n)",
            default="n"
        ).lower() == 'y'
        
        if not use_google:
            self.print_info("Google Sheets integration skipped")
            return
            
        # Get credentials file
        creds_path = self.prompt_for_value(
            "Path to Google service account JSON file"
        )
        
        if not Path(creds_path).exists():
            self.print_error(f"Credentials file not found: {creds_path}")
            return
            
        # Get spreadsheet ID
        spreadsheet_id = self.prompt_for_value(
            "Google Sheets ID (from the spreadsheet URL)"
        )
        
        # Clean the ID in case user pasted the full URL
        if "spreadsheets/d/" in spreadsheet_id:
            spreadsheet_id = spreadsheet_id.split("spreadsheets/d/")[1].split("/")[0]
            
        # Create settings directory
        self.settings_dir.mkdir(exist_ok=True)
        
        # Copy credentials file
        dest_path = self.settings_dir / "google_credentials.json"
        shutil.copy2(creds_path, dest_path)
        self.print_success(f"Credentials copied to: {dest_path}")
        
        # Update config.json
        config = {}
        if self.config_json_path.exists():
            with open(self.config_json_path, 'r') as f:
                config = json.load(f)
                
        if 'google_sheets_sync' not in config:
            config['google_sheets_sync'] = {}
            
        config['google_sheets_sync'].update({
            'enabled': True,
            'spreadsheet_id': spreadsheet_id,
            'credentials_path': str(dest_path)
        })
        
        with open(self.config_json_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        # Display service account email
        try:
            with open(dest_path, 'r') as f:
                creds_data = json.load(f)
                if 'client_email' in creds_data:
                    print(f"\n📧 Service Account Email: {creds_data['client_email']}")
                    print("⚠️  Make sure to share your Google Sheet with this email!")
        except:
            pass
            
        self.print_success("Google Sheets sync configured!")
        
        # Update .env with sheets ID
        if self.env_path.exists():
            with open(self.env_path, 'a') as f:
                f.write(f"\n# Google Sheets Configuration\n")
                f.write(f"AUTOTRAINX_SHEETS_ID={spreadsheet_id}\n")
                
    def start_sheets_daemon(self):
        """Start the Google Sheets sync daemon"""
        self.print_step(4, 4, "Starting Google Sheets Sync Daemon")
        
        if not self.check_google_sheets_configured():
            self.print_warning("Google Sheets not configured - skipping daemon start")
            return
            
        if self.check_daemon_running():
            self.print_info("Sheets sync daemon is already running")
            return
            
        start_daemon = self.prompt_for_value(
            "Start Google Sheets sync daemon? (y/n)",
            default="y"
        ).lower() == 'y'
        
        if not start_daemon:
            self.print_info("Daemon start skipped")
            return
            
        try:
            # Start the daemon
            subprocess.run([
                sys.executable,
                str(self.root_dir / "sheets_sync_daemon.py"),
                "--daemon"
            ], check=True)
            
            time.sleep(2)
            
            if self.check_daemon_running():
                self.print_success("Google Sheets sync daemon started successfully")
            else:
                self.print_warning("Daemon may have failed to start - check logs")
                
        except Exception as e:
            self.print_error(f"Failed to start daemon: {e}")
            
    def show_status(self):
        """Show current configuration status"""
        self.print_header("Current Configuration Status")
        
        state = self.check_current_state()
        
        # Environment status
        print(f"Environment (.env): {Colors.GREEN + '✓' if state['env_exists'] else Colors.RED + '✗'} "
              f"{'Configured' if state['env_exists'] else 'Not configured'}{Colors.NC}")
              
        # PostgreSQL status
        pg_status = ""
        if state['postgresql_installed']:
            if state['postgresql_running']:
                if state['postgresql_connection_ok']:
                    pg_status = f"{Colors.GREEN}✓ Running & Connected{Colors.NC}"
                else:
                    pg_status = f"{Colors.YELLOW}⚠ Running but connection failed{Colors.NC}"
            else:
                pg_status = f"{Colors.RED}✗ Not running{Colors.NC}"
        else:
            pg_status = f"{Colors.RED}✗ Not installed{Colors.NC}"
            
        print(f"PostgreSQL: {pg_status}")
              
        # Google Sheets status
        gs_status = ""
        if state['google_sheets_configured']:
            if state['google_sheets_connection_ok']:
                gs_status = f"{Colors.GREEN}✓ Configured & Connected{Colors.NC}"
            else:
                gs_status = f"{Colors.YELLOW}⚠ Configured but connection failed{Colors.NC}"
        else:
            gs_status = f"{Colors.RED}✗ Not configured{Colors.NC}"
            
        print(f"Google Sheets: {gs_status}")
              
        # Daemon status
        daemon_status = ""
        if state['daemon_running']:
            if state['daemon_healthy']:
                daemon_status = f"{Colors.GREEN}✓ Running & Healthy{Colors.NC}"
            else:
                daemon_status = f"{Colors.YELLOW}⚠ Running but not healthy{Colors.NC}"
        else:
            daemon_status = f"{Colors.RED}✗ Not running{Colors.NC}"
            
        print(f"Sync Daemon: {daemon_status}")
              
        if state['conflicts']:
            print(f"\n{Colors.YELLOW}Conflicts detected:{Colors.NC}")
            for conflict in state['conflicts']:
                print(f"  - {conflict}")
                
    def run(self, check_only: bool = False, fix_conflicts: bool = False, interactive: bool = True):
        """Run the unified setup process"""
        # Check current state
        state = self.check_current_state()
        
        # If interactive mode, show the menu
        if interactive and not check_only and not fix_conflicts:
            self.show_interactive_menu(state)
            return
            
        # Non-interactive mode (legacy behavior)
        self.print_header("AutoTrainX Unified Setup")
        
        # Show environment info
        if self.is_docker:
            self.print_info("Running in Docker environment")
        if self.is_root:
            self.print_info("Running as root user")
        
        # Show current status
        self.show_status()
        
        if check_only:
            return
            
        if fix_conflicts:
            self.fix_setup_conflicts()
            return
            
        # Determine what needs to be done
        print("\n" + "=" * 60)
        print("Setup will perform the following actions:")
        print("=" * 60)
        
        steps = []
        if not state['env_exists']:
            steps.append("1. Create secure .env configuration")
        else:
            steps.append("1. ✓ .env already configured")
            
        if state['conflicts'] or (not state['postgresql_installed'] and 
                                  self.config.get('DATABASE_TYPE', 'postgresql') == 'postgresql'):
            steps.append("2. Install and configure PostgreSQL")
        else:
            steps.append("2. ✓ PostgreSQL already configured")
            
        if not state['google_sheets_configured']:
            steps.append("3. Configure Google Sheets integration (optional)")
        else:
            steps.append("3. ✓ Google Sheets already configured")
            
        if state['google_sheets_configured'] and not state['daemon_running']:
            steps.append("4. Start Google Sheets sync daemon")
        else:
            steps.append("4. ✓ Sync daemon already running" if state['daemon_running'] else 
                        "4. - Sync daemon (requires Google Sheets)")
            
        for step in steps:
            print(f"  {step}")
            
        print("=" * 60)
        
        # Confirm to proceed
        proceed = self.prompt_for_value(
            "\nProceed with setup? (Y/n)",
            default="y"
        ).lower() != 'n'
        
        if not proceed:
            print("Setup cancelled.")
            return
            
        # Fix conflicts first if needed
        if state['conflicts']:
            self.fix_setup_conflicts()
            
        # Run setup steps
        try:
            # Step 1: Environment configuration
            if not state['env_exists']:
                self.setup_env_configuration()
            else:
                self.print_info("Using existing .env configuration")
                # Load existing config
                self.load_env_config()
                
            # Step 2: PostgreSQL setup
            if self.config.get('DATABASE_TYPE', 'postgresql') == 'postgresql':
                if not state['postgresql_installed'] or not state['postgresql_running']:
                    self.setup_postgresql()
                else:
                    self.print_info("PostgreSQL already configured")
                    # Test connection
                    self.print_info("Testing PostgreSQL connection...")
                    if self.test_postgresql_connection():
                        self.print_success("PostgreSQL connection successful!")
                    else:
                        self.print_warning("PostgreSQL connection failed - check credentials")
                    
            # Step 3: Google Sheets setup
            if not state['google_sheets_configured']:
                self.setup_google_sheets()
            else:
                self.print_info("Google Sheets already configured")
                # Test connection
                self.print_info("Testing Google Sheets API connection...")
                if self.test_google_sheets_connection():
                    self.print_success("Google Sheets API connection successful!")
                else:
                    self.print_warning("Google Sheets API connection failed - check credentials and permissions")
                
            # Step 4: Start daemon
            if self.check_google_sheets_configured():
                if not state['daemon_running']:
                    self.start_sheets_daemon()
                else:
                    self.print_info("Sheets sync daemon already running")
                    # Test health
                    self.print_info("Testing daemon health...")
                    if self.test_daemon_health():
                        self.print_success("Daemon is healthy and processing!")
                    else:
                        self.print_warning("Daemon is running but may not be healthy - check logs")
                
            # Final summary
            self.print_header("Setup Complete!")
            
            print("\n📋 Configuration Summary:")
            print(f"  - Environment: {self.env_path}")
            print(f"  - Database: {'PostgreSQL' if self.config.get('DATABASE_TYPE') == 'postgresql' else 'SQLite'}")
            if self.config.get('DATABASE_TYPE') == 'postgresql':
                print(f"    Host: {self.config.get('DATABASE_HOST', 'localhost')}")
                print(f"    Port: {self.config.get('DATABASE_PORT', '5432')}")
                print(f"    Database: {self.config.get('DATABASE_NAME', 'autotrainx')}")
                print(f"    User: {self.config.get('DATABASE_USER', 'autotrainx')}")
                
            if self.check_google_sheets_configured():
                print(f"  - Google Sheets: Configured")
                if self.check_daemon_running():
                    print(f"  - Sync Daemon: Running")
                    
            print("\n🚀 Next Steps:")
            print("  1. Activate virtual environment: source venv/bin/activate")
            print("  2. Start development servers: ./start_dev.sh")
            print("  3. Or run training: python main.py --menu")
            
            print("\n⚠️  Important:")
            print("  - Keep your .env file secure and never commit it to git")
            print("  - If you used generated passwords, save them securely")
            if self.check_google_sheets_configured():
                print("  - Make sure to share your Google Sheet with the service account email")
                
        except Exception as e:
            self.print_error(f"Setup failed: {e}")
            sys.exit(1)
            
    def load_env_config(self):
        """Load configuration from existing .env file"""
        if not self.env_path.exists():
            return
            
        with open(self.env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    self.config[key.strip()] = value.strip()
                    
    def get_key(self):
        """Get a single key press"""
        if not HAS_TERMIOS:
            # Fallback for systems without termios (e.g., Windows)
            return input()
            
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            key = sys.stdin.read(1)
            if key == '\x1b':  # ESC sequence
                key += sys.stdin.read(2)
            return key
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('clear' if os.name != 'nt' else 'cls')
        
    def show_interactive_menu(self, state: Dict[str, Any]):
        """Show interactive menu with arrow navigation"""
        # Determine available options
        options = []
        
        # Check if repair is needed
        needs_repair = (
            (state['postgresql_installed'] and state['postgresql_running'] and not state['postgresql_connection_ok']) or
            (state['google_sheets_configured'] and not state['google_sheets_connection_ok']) or
            (state['daemon_running'] and not state['daemon_healthy'])
        )
        
        if needs_repair:
            options.append(("repair", "🔧 Repair", "Fix connection issues"))
        else:
            options.append(("test", "🧪 Test", "Run all connection tests"))
            
        options.append(("config", "⚙️  Config", "Modify all settings"))
        options.append(("status", "📊 Status", "Show detailed status"))
        options.append(("exit", "🚪 Exit", "Exit setup"))
        
        current_index = 0
        
        while True:
            self.clear_screen()
            self.print_header("AutoTrainX Unified Setup - Interactive Menu")
            
            # Show quick status
            print(f"PostgreSQL: {self._get_status_icon(state, 'postgresql')}")
            print(f"Google Sheets: {self._get_status_icon(state, 'google_sheets')}")
            print(f"Sync Daemon: {self._get_status_icon(state, 'daemon')}")
            print()
            
            # Show menu options
            for i, (key, label, description) in enumerate(options):
                if i == current_index:
                    print(f"{Colors.CYAN}▶ {label}{Colors.NC} - {description}")
                else:
                    print(f"  {label} - {description}")
                    
            print(f"\n{Colors.YELLOW}Use ↑/↓ arrows to navigate, Enter to select, or 'q' to quit{Colors.NC}")
            
            # Get key press
            key = self.get_key()
            
            if key == '\x1b[A':  # Up arrow
                current_index = (current_index - 1) % len(options)
            elif key == '\x1b[B':  # Down arrow
                current_index = (current_index + 1) % len(options)
            elif key == '\r' or key == '\n':  # Enter
                selected = options[current_index][0]
                if selected == "repair":
                    self.show_repair_menu(state)
                elif selected == "test":
                    self.run_all_tests()
                elif selected == "config":
                    self.show_config_menu()
                elif selected == "status":
                    self.show_detailed_status(state)
                elif selected == "exit":
                    break
                # Refresh state after action
                state = self.check_current_state()
            elif key.lower() == 'q':
                break
                
    def _get_status_icon(self, state: Dict[str, Any], component: str) -> str:
        """Get status icon for a component"""
        if component == 'postgresql':
            if state['postgresql_installed']:
                if state['postgresql_running']:
                    if state['postgresql_connection_ok']:
                        return f"{Colors.GREEN}✓ Connected{Colors.NC}"
                    else:
                        return f"{Colors.YELLOW}⚠ Connection failed{Colors.NC}"
                else:
                    return f"{Colors.RED}✗ Not running{Colors.NC}"
            else:
                return f"{Colors.RED}✗ Not installed{Colors.NC}"
        elif component == 'google_sheets':
            if state['google_sheets_configured']:
                if state['google_sheets_connection_ok']:
                    return f"{Colors.GREEN}✓ Connected{Colors.NC}"
                else:
                    return f"{Colors.YELLOW}⚠ Connection failed{Colors.NC}"
            else:
                return f"{Colors.RED}✗ Not configured{Colors.NC}"
        elif component == 'daemon':
            if state['daemon_running']:
                if state['daemon_healthy']:
                    return f"{Colors.GREEN}✓ Healthy{Colors.NC}"
                else:
                    return f"{Colors.YELLOW}⚠ Not healthy{Colors.NC}"
            else:
                return f"{Colors.RED}✗ Not running{Colors.NC}"
                
    def show_repair_menu(self, state: Dict[str, Any]):
        """Show repair options for failed components"""
        self.clear_screen()
        self.print_header("Repair Menu")
        
        repairs_needed = []
        
        if state['postgresql_installed'] and state['postgresql_running'] and not state['postgresql_connection_ok']:
            repairs_needed.append(("postgresql", "Fix PostgreSQL connection"))
        
        if state['google_sheets_configured'] and not state['google_sheets_connection_ok']:
            repairs_needed.append(("google_sheets", "Fix Google Sheets API connection"))
            
        if state['daemon_running'] and not state['daemon_healthy']:
            repairs_needed.append(("daemon", "Restart sync daemon"))
            
        repairs_needed.append(("back", "Back to main menu"))
        
        current_index = 0
        
        while True:
            self.clear_screen()
            self.print_header("Repair Menu")
            
            print("Select component to repair:\n")
            
            for i, (key, label) in enumerate(repairs_needed):
                if i == current_index:
                    print(f"{Colors.CYAN}▶ {label}{Colors.NC}")
                else:
                    print(f"  {label}")
                    
            key = self.get_key()
            
            if key == '\x1b[A':  # Up arrow
                current_index = (current_index - 1) % len(repairs_needed)
            elif key == '\x1b[B':  # Down arrow
                current_index = (current_index + 1) % len(repairs_needed)
            elif key == '\r' or key == '\n':  # Enter
                selected = repairs_needed[current_index][0]
                if selected == "postgresql":
                    self.repair_postgresql()
                elif selected == "google_sheets":
                    self.repair_google_sheets()
                elif selected == "daemon":
                    self.repair_daemon()
                elif selected == "back":
                    break
                    
            input("\nPress Enter to continue...")
            
    def run_all_tests(self):
        """Run all connection tests"""
        self.clear_screen()
        self.print_header("Running All Tests")
        
        # Load config
        self.load_env_config()
        
        # Test PostgreSQL
        print("\n1. Testing PostgreSQL...")
        if self.test_postgresql_connection():
            self.print_success("PostgreSQL connection successful!")
        else:
            self.print_error("PostgreSQL connection failed")
            
        # Test Google Sheets
        print("\n2. Testing Google Sheets API...")
        if self.test_google_sheets_connection():
            self.print_success("Google Sheets API connection successful!")
        else:
            self.print_error("Google Sheets API connection failed")
            
        # Test daemon
        print("\n3. Testing sync daemon...")
        if self.test_daemon_health():
            self.print_success("Daemon is healthy!")
        else:
            self.print_error("Daemon health check failed")
            
        input("\nPress Enter to continue...")
        
    def show_config_menu(self):
        """Show configuration menu"""
        options = [
            ("env", "Environment (.env) settings"),
            ("postgresql", "PostgreSQL settings"),
            ("google_sheets", "Google Sheets settings"),
            ("daemon", "Sync daemon settings"),
            ("back", "Back to main menu")
        ]
        
        current_index = 0
        
        while True:
            self.clear_screen()
            self.print_header("Configuration Menu")
            
            print("Select configuration to modify:\n")
            
            for i, (key, label) in enumerate(options):
                if i == current_index:
                    print(f"{Colors.CYAN}▶ {label}{Colors.NC}")
                else:
                    print(f"  {label}")
                    
            key = self.get_key()
            
            if key == '\x1b[A':  # Up arrow
                current_index = (current_index - 1) % len(options)
            elif key == '\x1b[B':  # Down arrow
                current_index = (current_index + 1) % len(options)
            elif key == '\r' or key == '\n':  # Enter
                selected = options[current_index][0]
                if selected == "env":
                    self.configure_env_interactive()
                elif selected == "postgresql":
                    self.configure_postgresql_interactive()
                elif selected == "google_sheets":
                    self.configure_google_sheets_interactive()
                elif selected == "daemon":
                    self.configure_daemon_interactive()
                elif selected == "back":
                    break
                    
    def show_detailed_status(self, state: Dict[str, Any]):
        """Show detailed status information"""
        self.clear_screen()
        self.print_header("Detailed Status")
        
        # PostgreSQL details
        print(f"\n{Colors.BOLD}PostgreSQL:{Colors.NC}")
        print(f"  Installed: {'Yes' if state['postgresql_installed'] else 'No'}")
        print(f"  Running: {'Yes' if state['postgresql_running'] else 'No'}")
        print(f"  Connection OK: {'Yes' if state['postgresql_connection_ok'] else 'No'}")
        if self.config.get('DATABASE_HOST'):
            print(f"  Host: {self.config.get('DATABASE_HOST', 'localhost')}")
            print(f"  Port: {self.config.get('DATABASE_PORT', '5432')}")
            print(f"  Database: {self.config.get('DATABASE_NAME', 'autotrainx')}")
            print(f"  User: {self.config.get('DATABASE_USER', 'autotrainx')}")
            
        # Google Sheets details
        print(f"\n{Colors.BOLD}Google Sheets:{Colors.NC}")
        print(f"  Configured: {'Yes' if state['google_sheets_configured'] else 'No'}")
        print(f"  API Connection OK: {'Yes' if state['google_sheets_connection_ok'] else 'No'}")
        if state['google_sheets_configured']:
            try:
                with open(self.config_json_path, 'r') as f:
                    config = json.load(f)
                    gs_config = config.get('google_sheets_sync', {})
                    print(f"  Spreadsheet ID: {gs_config.get('spreadsheet_id', 'Not set')}")
                    print(f"  Credentials: {gs_config.get('credentials_path', 'Not set')}")
            except:
                pass
                
        # Daemon details
        print(f"\n{Colors.BOLD}Sync Daemon:{Colors.NC}")
        print(f"  Running: {'Yes' if state['daemon_running'] else 'No'}")
        print(f"  Healthy: {'Yes' if state['daemon_healthy'] else 'No'}")
        if state['daemon_running']:
            try:
                pid = int(self.daemon_pid_file.read_text().strip())
                print(f"  PID: {pid}")
            except:
                pass
                
        input("\nPress Enter to continue...")
        
    def repair_postgresql(self):
        """Repair PostgreSQL connection"""
        self.clear_screen()
        self.print_header("Repairing PostgreSQL Connection")
        
        # Try to restart PostgreSQL
        print("1. Restarting PostgreSQL service...")
        if self.is_docker:
            subprocess.run(['service', 'postgresql', 'restart'], capture_output=True)
        else:
            self.run_privileged_command(['service', 'postgresql', 'restart'])
        time.sleep(3)
        
        # Test connection
        print("\n2. Testing connection...")
        if self.test_postgresql_connection():
            self.print_success("PostgreSQL connection restored!")
        else:
            print("\n3. Resetting authentication...")
            self.configure_postgresql_docker_auth()
            if self.test_postgresql_connection():
                self.print_success("PostgreSQL connection restored!")
            else:
                self.print_error("Failed to restore connection")
                print("\nTry running: python unified_setup.py --fix-conflicts")
                
    def repair_google_sheets(self):
        """Repair Google Sheets connection"""
        self.clear_screen()
        self.print_header("Repairing Google Sheets Connection")
        
        print("Checking Google Sheets configuration...")
        
        # Verify credentials file exists
        try:
            with open(self.config_json_path, 'r') as f:
                config = json.load(f)
                gs_config = config.get('google_sheets_sync', {})
                creds_path = gs_config.get('credentials_path')
                
                if not Path(creds_path).exists():
                    self.print_error(f"Credentials file not found: {creds_path}")
                    print("\nPlease reconfigure Google Sheets in the Config menu")
                else:
                    # Test API connection
                    if self.test_google_sheets_connection():
                        self.print_success("Google Sheets connection restored!")
                    else:
                        self.print_error("API connection failed")
                        print("\nPossible issues:")
                        print("1. Check that the spreadsheet is shared with the service account")
                        print("2. Verify the spreadsheet ID is correct")
                        print("3. Check internet connectivity")
        except Exception as e:
            self.print_error(f"Error: {e}")
            
    def repair_daemon(self):
        """Restart sync daemon"""
        self.clear_screen()
        self.print_header("Restarting Sync Daemon")
        
        # Stop daemon
        print("1. Stopping daemon...")
        subprocess.run([sys.executable, str(self.root_dir / "sheets_sync_daemon.py"), "--stop"], 
                      capture_output=True)
        time.sleep(2)
        
        # Start daemon
        print("2. Starting daemon...")
        subprocess.run([sys.executable, str(self.root_dir / "sheets_sync_daemon.py"), "--daemon"], 
                      capture_output=True)
        time.sleep(3)
        
        # Check health
        if self.test_daemon_health():
            self.print_success("Daemon restarted successfully!")
        else:
            self.print_error("Daemon restart failed")
            print("\nCheck logs at: logs/sheets_sync_daemon.log")
            
    def configure_env_interactive(self):
        """Interactive environment configuration"""
        self.clear_screen()
        self.print_header("Environment Configuration")
        
        # Load current config
        self.load_env_config()
        
        options = [
            ("db_type", "Database Type", self.config.get('DATABASE_TYPE', 'postgresql')),
            ("db_host", "Database Host", self.config.get('DATABASE_HOST', 'localhost')),
            ("db_port", "Database Port", self.config.get('DATABASE_PORT', '5432')),
            ("db_name", "Database Name", self.config.get('DATABASE_NAME', 'autotrainx')),
            ("db_user", "Database User", self.config.get('DATABASE_USER', 'autotrainx')),
            ("db_pass", "Database Password", "********"),
            ("api_key", "API Secret Key", "********"),
            ("jwt_key", "JWT Secret Key", "********"),
            ("save", "Save Changes", ""),
            ("back", "Back", "")
        ]
        
        current_index = 0
        
        while True:
            self.clear_screen()
            self.print_header("Environment Configuration")
            
            for i, (key, label, value) in enumerate(options):
                if i == current_index:
                    print(f"{Colors.CYAN}▶ {label}: {value}{Colors.NC}")
                else:
                    print(f"  {label}: {value}")
                    
            key = self.get_key()
            
            if key == '\x1b[A':  # Up arrow
                current_index = (current_index - 1) % len(options)
            elif key == '\x1b[B':  # Down arrow
                current_index = (current_index + 1) % len(options)
            elif key == '\r' or key == '\n':  # Enter
                selected = options[current_index][0]
                if selected == "save":
                    self.write_env_file()
                    self.print_success("Configuration saved!")
                    input("\nPress Enter to continue...")
                    break
                elif selected == "back":
                    break
                elif selected == "db_pass":
                    new_value = getpass.getpass("Enter new database password: ")
                    if new_value:
                        self.config['DATABASE_PASSWORD'] = new_value
                elif selected == "api_key":
                    if self.prompt_for_value("Generate new API key? (y/n)", "n").lower() == 'y':
                        self.config['API_SECRET_KEY'] = self.generate_secret_key()
                        self.print_success("New API key generated!")
                elif selected == "jwt_key":
                    if self.prompt_for_value("Generate new JWT key? (y/n)", "n").lower() == 'y':
                        self.config['JWT_SECRET_KEY'] = self.generate_secret_key()
                        self.print_success("New JWT key generated!")
                else:
                    # Edit other fields
                    print(f"\nEditing {options[current_index][1]}")
                    new_value = input(f"New value [{options[current_index][2]}]: ")
                    if new_value:
                        if selected == "db_type":
                            self.config['DATABASE_TYPE'] = new_value
                        elif selected == "db_host":
                            self.config['DATABASE_HOST'] = new_value
                        elif selected == "db_port":
                            self.config['DATABASE_PORT'] = new_value
                        elif selected == "db_name":
                            self.config['DATABASE_NAME'] = new_value
                        elif selected == "db_user":
                            self.config['DATABASE_USER'] = new_value
                        # Update display
                        options[current_index] = (selected, options[current_index][1], new_value)
                        
    def configure_postgresql_interactive(self):
        """Interactive PostgreSQL configuration"""
        self.clear_screen()
        self.print_header("PostgreSQL Configuration")
        
        print("PostgreSQL configuration options:")
        print("\n1. Reset database password")
        print("2. Recreate database and user")
        print("3. Configure authentication (pg_hba.conf)")
        print("4. Back to config menu")
        
        choice = input("\nSelect option: ")
        
        if choice == "1":
            new_pass = getpass.getpass("Enter new password: ")
            confirm = getpass.getpass("Confirm password: ")
            if new_pass == confirm:
                # Update password in PostgreSQL
                try:
                    sql = f"ALTER USER autotrainx WITH PASSWORD '{new_pass}';"
                    if self.is_root or self.is_docker:
                        subprocess.run(['su', '-', 'postgres', '-c', f'psql -c "{sql}"'], check=True)
                    else:
                        subprocess.run(['sudo', '-u', 'postgres', 'psql', '-c', sql], check=True)
                    
                    # Update .env
                    self.config['DATABASE_PASSWORD'] = new_pass
                    self.write_env_file()
                    self.print_success("Password updated successfully!")
                except Exception as e:
                    self.print_error(f"Failed to update password: {e}")
            else:
                self.print_error("Passwords don't match!")
                
        elif choice == "2":
            if self.prompt_for_value("This will recreate the database. Continue? (y/n)", "n").lower() == 'y':
                self.setup_postgresql()
                
        elif choice == "3":
            self.configure_postgresql_docker_auth()
            self.print_success("Authentication reconfigured!")
            
        input("\nPress Enter to continue...")
        
    def configure_google_sheets_interactive(self):
        """Interactive Google Sheets configuration"""
        self.clear_screen()
        self.print_header("Google Sheets Configuration")
        
        print("1. Update spreadsheet ID")
        print("2. Update credentials file")
        print("3. Test connection")
        print("4. Back to config menu")
        
        choice = input("\nSelect option: ")
        
        if choice == "1":
            new_id = input("Enter new spreadsheet ID: ")
            if new_id:
                try:
                    # Update config.json
                    config = {}
                    if self.config_json_path.exists():
                        with open(self.config_json_path, 'r') as f:
                            config = json.load(f)
                    
                    if 'google_sheets_sync' not in config:
                        config['google_sheets_sync'] = {}
                        
                    config['google_sheets_sync']['spreadsheet_id'] = new_id
                    
                    with open(self.config_json_path, 'w') as f:
                        json.dump(config, f, indent=2)
                        
                    self.print_success("Spreadsheet ID updated!")
                except Exception as e:
                    self.print_error(f"Failed to update: {e}")
                    
        elif choice == "2":
            creds_path = input("Enter path to credentials JSON file: ")
            if creds_path and Path(creds_path).exists():
                self.setup_google_sheets()
                
        elif choice == "3":
            if self.test_google_sheets_connection():
                self.print_success("Connection successful!")
            else:
                self.print_error("Connection failed!")
                
        input("\nPress Enter to continue...")
        
    def configure_daemon_interactive(self):
        """Interactive daemon configuration"""
        self.clear_screen()
        self.print_header("Sync Daemon Configuration")
        
        print("1. Start daemon")
        print("2. Stop daemon")
        print("3. Restart daemon")
        print("4. View daemon logs")
        print("5. Back to config menu")
        
        choice = input("\nSelect option: ")
        
        if choice == "1":
            subprocess.run([sys.executable, str(self.root_dir / "sheets_sync_daemon.py"), "--daemon"])
            self.print_success("Daemon started!")
            
        elif choice == "2":
            subprocess.run([sys.executable, str(self.root_dir / "sheets_sync_daemon.py"), "--stop"])
            self.print_success("Daemon stopped!")
            
        elif choice == "3":
            self.repair_daemon()
            
        elif choice == "4":
            log_file = self.root_dir / "logs" / "sheets_sync_daemon.log"
            if log_file.exists():
                # Show last 20 lines
                subprocess.run(['tail', '-n', '20', str(log_file)])
            else:
                self.print_error("Log file not found")
                
        input("\nPress Enter to continue...")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="AutoTrainX Unified Setup Script"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Check current configuration status without making changes"
    )
    parser.add_argument(
        "--fix-conflicts",
        action="store_true",
        help="Fix conflicts with setup.sh configuration"
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Run in non-interactive mode (legacy behavior)"
    )
    
    args = parser.parse_args()
    
    # Create and run setup
    setup = UnifiedSetup()
    
    try:
        setup.run(
            check_only=args.check_only, 
            fix_conflicts=args.fix_conflicts,
            interactive=not args.no_interactive
        )
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
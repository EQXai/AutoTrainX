#!/usr/bin/env python3
"""
AutoTrainX Integrations Manager v2.0

Unified installation and configuration interface for AutoTrainX integrations:
- PostgreSQL database installation and configuration
- Google Sheets synchronization setup
- Sync Daemon management
- General security and CORS configuration

Each integration manages its own environment variables in .env file.
"""

import sys
import os
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
from dataclasses import dataclass
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

# Try to import questionary
try:
    import questionary
    from questionary import Style
except ImportError:
    print("Error: questionary library not found.")
    print("Please install it with: pip install questionary")
    sys.exit(1)

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

# Custom styling matching AutoTrainX main menu
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
class IntegrationResult:
    """Result of an integration operation."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class IntegrationsManager:
    """Manages AutoTrainX integrations installation and configuration."""
    
    def __init__(self):
        """Initialize the integrations manager."""
        self.base_path = Path(__file__).parent
        self.env_path = self.base_path / ".env"
        self.settings_path = self.base_path / "settings"
        self.settings_path.mkdir(exist_ok=True)
        self.running = True
        
        # Component status tracking
        self.components_status = {
            'postgresql': {'installed': False, 'configured': False},
            'google_sheets': {'installed': False, 'configured': False},
            'sync_daemon': {'installed': True, 'configured': False}  # Python-based, no separate install
        }
        
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def show_header(self):
        """Show the application header."""
        self.clear_screen()
        print("\033[1;36m" + "="*60 + "\033[0m")
        print("\033[1;36m" + "         AUTOTRAINX INTEGRATIONS MANAGER".center(60) + "\033[0m")
        print("\033[1;36m" + "                  Version 2.0".center(60) + "\033[0m")
        print("\033[1;36m" + "="*60 + "\033[0m")
        print()
        
    def show_status_line(self):
        """Show system status line."""
        # Check component status
        pg_status = "✓" if self._check_postgresql_installed() else "✗"
        gs_status = "✓" if self._check_google_sheets_installed() else "✗"
        daemon_status = "✓" if self._check_daemon_running() else "✗"
        
        print("\033[90m" + "─"*60 + "\033[0m")
        print(f"PostgreSQL: {pg_status}  |  Google Sheets: {gs_status}  |  Sync Daemon: {daemon_status}")
        print("\033[90m" + "─"*60 + "\033[0m")
        print()
        
    def main_menu(self):
        """Display the main menu."""
        while self.running:
            self.show_header()
            self.show_status_line()
            
            choices = [
                "🔧 Installation",
                "⚙️  Configuration", 
                "✅ Verify System",
                "❌ Exit"
            ]
            
            choice = questionary.select(
                "What would you like to do?",
                choices=choices,
                style=AUTOTRAINX_STYLE,
                use_shortcuts=True,
                use_arrow_keys=True
            ).ask()
            
            if choice is None:  # Ctrl+C
                self.running = False
                break
                
            if "Installation" in choice:
                self.installation_menu()
            elif "Configuration" in choice:
                self.configuration_menu()
            elif "Verify" in choice:
                self.verify_system()
            elif "Exit" in choice:
                self.running = False
                
    def installation_menu(self):
        """Display the installation menu."""
        while True:
            self.show_header()
            print("\033[1;33m=== INSTALLATION MENU ===\033[0m\n")
            
            # Check current status
            pg_installed = self._check_postgresql_installed()
            gs_installed = self._check_google_sheets_installed()
            
            choices = []
            if not pg_installed:
                choices.append("🐘 Install PostgreSQL")
            else:
                choices.append("✓ PostgreSQL (Already Installed)")
                
            if not gs_installed:
                choices.append("📊 Install Google Sheets Dependencies")
            else:
                choices.append("✓ Google Sheets Dependencies (Already Installed)")
                
            choices.extend([
                "🔄 Install Sync Daemon Dependencies",
                "📦 Install All Missing Components",
                "⬅️  Back to Main Menu"
            ])
            
            choice = questionary.select(
                "Select component to install:",
                choices=choices,
                style=AUTOTRAINX_STYLE,
                use_shortcuts=True,
                use_arrow_keys=True
            ).ask()
            
            if choice is None or "Back" in choice:
                break
                
            if "PostgreSQL" in choice and "Already" not in choice:
                self._install_postgresql()
            elif "Google Sheets" in choice and "Already" not in choice:
                self._install_google_sheets()
            elif "Sync Daemon" in choice:
                self._install_sync_daemon()
            elif "All Missing" in choice:
                if not pg_installed:
                    self._install_postgresql()
                if not gs_installed:
                    self._install_google_sheets()
                self._install_sync_daemon()
                    
    def configuration_menu(self):
        """Display the configuration menu."""
        while True:
            self.show_header()
            print("\033[1;33m=== CONFIGURATION MENU ===\033[0m\n")
            
            choices = [
                "🐘 Configure PostgreSQL",
                "📊 Configure Google Sheets",
                "🔄 Configure Sync Daemon",
                "🔐 Configure Security (API Keys, CORS)",
                "⚡ Quick Setup (Configure All)",
                "⬅️  Back to Main Menu"
            ]
            
            choice = questionary.select(
                "Select component to configure:",
                choices=choices,
                style=AUTOTRAINX_STYLE,
                use_shortcuts=True,
                use_arrow_keys=True
            ).ask()
            
            if choice is None or "Back" in choice:
                break
                
            if "PostgreSQL" in choice:
                self._configure_postgresql()
            elif "Google Sheets" in choice:
                self._configure_google_sheets()
            elif "Sync Daemon" in choice:
                self._configure_sync_daemon()
            elif "Security" in choice:
                self._configure_security()
            elif "Quick Setup" in choice:
                self._quick_setup()
                
    def verify_system(self):
        """Verify all system configurations."""
        self.show_header()
        print("\033[1;33m=== SYSTEM VERIFICATION ===\033[0m\n")
        
        env_vars = self._load_env_file()
        errors = []
        warnings = []
        
        # PostgreSQL Verification
        print("\033[1;36mPostgreSQL Database:\033[0m")
        pg_vars = ['DATABASE_HOST', 'DATABASE_PORT', 'DATABASE_NAME', 'DATABASE_USER', 'DATABASE_PASSWORD']
        pg_configured = all(env_vars.get(var) for var in pg_vars)
        
        for var in pg_vars:
            if var in env_vars and env_vars[var]:
                if var == 'DATABASE_PASSWORD':
                    print(f"  ✓ {var}: ****")
                else:
                    print(f"  ✓ {var}: {env_vars[var]}")
            else:
                print(f"  ✗ {var}: Not configured")
                errors.append(f"PostgreSQL: {var} missing")
                
        # Test connection
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
                print("  ✓ Connection test: \033[92mSUCCESS\033[0m")
            except Exception as e:
                print(f"  ✗ Connection test: \033[91mFAILED\033[0m - {str(e)}")
                errors.append("PostgreSQL: Connection failed")
        elif not HAS_PSYCOPG2:
            print("  ⚠ Connection test: Skipped (psycopg2 not installed)")
            warnings.append("PostgreSQL: psycopg2 not installed")
            
        print()
        
        # Google Sheets Verification
        print("\033[1;36mGoogle Sheets Integration:\033[0m")
        google_vars = ['GOOGLE_SERVICE_ACCOUNT_EMAIL', 'GOOGLE_PROJECT_ID', 
                      'GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY', 'AUTOTRAINX_SHEETS_ID']
        google_configured = all(env_vars.get(var) for var in google_vars)
        
        for var in google_vars:
            if var in env_vars and env_vars[var]:
                if 'PRIVATE_KEY' in var:
                    print(f"  ✓ {var}: ****")
                else:
                    print(f"  ✓ {var}: {env_vars[var]}")
            else:
                print(f"  ✗ {var}: Not configured")
                errors.append(f"Google Sheets: {var} missing")
                
        # Test authentication
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
                print("  ✓ Authentication test: \033[92mSUCCESS\033[0m")
            except Exception as e:
                print(f"  ✗ Authentication test: \033[91mFAILED\033[0m - {str(e)}")
                errors.append("Google Sheets: Authentication failed")
        elif not HAS_GOOGLE_AUTH:
            print("  ⚠ Authentication test: Skipped (google-auth not installed)")
            warnings.append("Google Sheets: Libraries not installed")
            
        print()
        
        # Security Configuration
        print("\033[1;36mSecurity Configuration:\033[0m")
        security_vars = ['API_SECRET_KEY', 'JWT_SECRET_KEY']
        
        for var in security_vars:
            if var in env_vars and env_vars[var]:
                print(f"  ✓ {var}: ****")
            else:
                print(f"  ✗ {var}: Not configured")
                errors.append(f"Security: {var} missing")
                
        print()
        
        # Sync Daemon Status
        print("\033[1;36mSync Daemon:\033[0m")
        if self._check_daemon_running():
            print("  ✓ Status: \033[92mRUNNING\033[0m")
        else:
            print("  ⚠ Status: \033[93mNOT RUNNING\033[0m")
            warnings.append("Sync daemon not running")
            
        # Summary
        print("\n" + "="*60)
        if not errors and not warnings:
            print("\033[92m✓ All systems configured correctly!\033[0m")
        else:
            if errors:
                print(f"\033[91mErrors found ({len(errors)}):\033[0m")
                for error in errors:
                    print(f"  • {error}")
                    
            if warnings:
                print(f"\n\033[93mWarnings ({len(warnings)}):\033[0m")
                for warning in warnings:
                    print(f"  • {warning}")
                    
        questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        
    # ==================== Installation Methods ====================
    
    def _install_postgresql(self):
        """Install PostgreSQL."""
        self.show_header()
        print("\033[1;33m=== POSTGRESQL INSTALLATION ===\033[0m\n")
        
        # Check if already installed
        if self._check_postgresql_installed():
            print("✓ PostgreSQL is already installed.")
            if not questionary.confirm(
                "Do you want to reinstall?",
                default=False,
                style=AUTOTRAINX_STYLE
            ).ask():
                return
                
        print("\n📦 Installing PostgreSQL...")
        print("This may take a few minutes...\n")
        
        # Update package list
        subprocess.run(['sudo', 'apt-get', 'update'], check=False)
        
        # Install PostgreSQL
        cmd = ['sudo', 'apt-get', 'install', '-y', 'postgresql', 'postgresql-contrib', 'postgresql-client']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("\n✅ PostgreSQL installed successfully!")
            
            # Install Python adapter
            print("\n📦 Installing psycopg2...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'psycopg2-binary'], check=False)
            
            print("\n✅ Installation complete!")
        else:
            print(f"\n❌ Failed to install PostgreSQL: {result.stderr}")
            
        questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        
    def _install_google_sheets(self):
        """Install Google Sheets dependencies."""
        self.show_header()
        print("\033[1;33m=== GOOGLE SHEETS DEPENDENCIES ===\033[0m\n")
        
        deps = [
            'google-api-python-client',
            'google-auth',
            'google-auth-oauthlib',
            'google-auth-httplib2',
            'gspread'
        ]
        
        print("📦 Installing Google Sheets API dependencies...")
        print("Packages to install:")
        for dep in deps:
            print(f"  • {dep}")
        print()
        
        cmd = [sys.executable, '-m', 'pip', 'install'] + deps
        result = subprocess.run(cmd)
        
        if result.returncode == 0:
            print("\n✅ Google Sheets dependencies installed successfully!")
        else:
            print("\n❌ Failed to install some dependencies")
            
        questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        
    def _install_sync_daemon(self):
        """Install sync daemon dependencies."""
        self.show_header()
        print("\033[1;33m=== SYNC DAEMON DEPENDENCIES ===\033[0m\n")
        
        deps = ['psutil', 'python-daemon']
        
        print("📦 Installing sync daemon dependencies...")
        print("Packages to install:")
        for dep in deps:
            print(f"  • {dep}")
        print()
        
        cmd = [sys.executable, '-m', 'pip', 'install'] + deps
        result = subprocess.run(cmd)
        
        if result.returncode == 0:
            print("\n✅ Sync daemon dependencies installed successfully!")
        else:
            print("\n⚠️  Some dependencies might not be available (not critical)")
            
        questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        
    # ==================== Configuration Methods ====================
    
    def _configure_postgresql(self):
        """Configure PostgreSQL database."""
        self.show_header()
        print("\033[1;33m=== POSTGRESQL CONFIGURATION ===\033[0m\n")
        
        env_vars = self._load_env_file()
        
        print("Enter PostgreSQL configuration:\n")
        
        # Basic configuration
        db_host = questionary.text(
            "Database Host:",
            default=env_vars.get('DATABASE_HOST', 'localhost'),
            style=AUTOTRAINX_STYLE
        ).ask()
        
        db_port = questionary.text(
            "Database Port:",
            default=env_vars.get('DATABASE_PORT', '5432'),
            style=AUTOTRAINX_STYLE
        ).ask()
        
        db_name = questionary.text(
            "Database Name:",
            default=env_vars.get('DATABASE_NAME', 'autotrainx'),
            style=AUTOTRAINX_STYLE
        ).ask()
        
        db_user = questionary.text(
            "Database User:",
            default=env_vars.get('DATABASE_USER', 'autotrainx'),
            style=AUTOTRAINX_STYLE
        ).ask()
        
        # Password handling
        current_password = env_vars.get('DATABASE_PASSWORD', '')
        if current_password:
            change_password = questionary.confirm(
                "Change database password?",
                default=False,
                style=AUTOTRAINX_STYLE
            ).ask()
        else:
            change_password = True
            
        if change_password:
            db_password = questionary.password(
                "Database Password:",
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if not db_password:
                print("\n❌ Password cannot be empty")
                questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
                return
        else:
            db_password = current_password
            
        # Advanced options
        show_advanced = questionary.confirm(
            "\nConfigure advanced options?",
            default=False,
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if show_advanced:
            pool_size = questionary.text(
                "Connection Pool Size:",
                default=env_vars.get('DATABASE_POOL_SIZE', '10'),
                style=AUTOTRAINX_STYLE
            ).ask()
            
            echo_sql = questionary.select(
                "Echo SQL statements?",
                choices=['false', 'true'],
                default=env_vars.get('DATABASE_ECHO', 'false'),
                style=AUTOTRAINX_STYLE
            ).ask()
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
        
        self._update_env_variables(updates)
        print("\n✅ PostgreSQL configuration saved!")
        
        # Offer to create database
        if questionary.confirm(
            "\nCreate database and user now?",
            default=True,
            style=AUTOTRAINX_STYLE
        ).ask():
            self._create_postgresql_database(db_name, db_user, db_password)
            
        questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        
    def _configure_google_sheets(self):
        """Configure Google Sheets integration."""
        self.show_header()
        print("\033[1;33m=== GOOGLE SHEETS CONFIGURATION ===\033[0m\n")
        
        env_vars = self._load_env_file()
        
        # Method selection
        method = questionary.select(
            "Select authentication method:",
            choices=[
                "📄 Use service account JSON file (recommended)",
                "⌨️  Enter credentials manually"
            ],
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if "JSON file" in method:
            json_path = questionary.path(
                "Path to service account JSON file:",
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if not os.path.exists(json_path):
                print("\n❌ File not found")
                questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
                return
                
            try:
                with open(json_path, 'r') as f:
                    creds_data = json.load(f)
                    
                service_email = creds_data.get('client_email')
                project_id = creds_data.get('project_id')
                private_key = creds_data.get('private_key')
                
                if not all([service_email, project_id, private_key]):
                    print("\n❌ Invalid credentials file")
                    questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
                    return
                    
                # Copy to settings
                dest_path = self.settings_path / "google_credentials.json"
                shutil.copy2(json_path, dest_path)
                print(f"\n✅ Credentials copied to {dest_path}")
                
            except Exception as e:
                print(f"\n❌ Failed to read credentials: {e}")
                questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
                return
        else:
            # Manual entry
            service_email = questionary.text(
                "Service Account Email:",
                default=env_vars.get('GOOGLE_SERVICE_ACCOUNT_EMAIL', ''),
                style=AUTOTRAINX_STYLE
            ).ask()
            
            project_id = questionary.text(
                "Project ID:",
                default=env_vars.get('GOOGLE_PROJECT_ID', ''),
                style=AUTOTRAINX_STYLE
            ).ask()
            
            print("\nPaste the private key (Ctrl+D when done):")
            private_key_lines = []
            try:
                while True:
                    line = input()
                    private_key_lines.append(line)
            except EOFError:
                pass
                
            private_key = '\\n'.join(private_key_lines)
            
        # Spreadsheet ID
        spreadsheet_id = questionary.text(
            "\nGoogle Sheets Spreadsheet ID:",
            default=env_vars.get('AUTOTRAINX_SHEETS_ID', ''),
            style=AUTOTRAINX_STYLE
        ).ask()
        
        # Clean ID if URL provided
        if "spreadsheets/d/" in spreadsheet_id:
            spreadsheet_id = spreadsheet_id.split("spreadsheets/d/")[1].split("/")[0]
            
        # Update environment
        updates = {
            'GOOGLE_SERVICE_ACCOUNT_EMAIL': service_email,
            'GOOGLE_PROJECT_ID': project_id,
            'GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY': private_key,
            'AUTOTRAINX_SHEETS_ID': spreadsheet_id
        }
        
        self._update_env_variables(updates)
        
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
            
        print(f"\n✅ Google Sheets configuration saved!")
        print(f"\n⚠️  Remember to share your spreadsheet with:\n   {service_email}")
        
        questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        
    def _configure_sync_daemon(self):
        """Configure sync daemon."""
        self.show_header()
        print("\033[1;33m=== SYNC DAEMON CONFIGURATION ===\033[0m\n")
        
        print("ℹ️  Sync daemon uses settings from settings/config.json")
        
        # Check if daemon is running
        if self._check_daemon_running():
            print("\n✅ Sync daemon is currently RUNNING")
            
            if questionary.confirm(
                "\nRestart daemon with new settings?",
                default=True,
                style=AUTOTRAINX_STYLE
            ).ask():
                self._restart_sync_daemon()
        else:
            print("\n⚠️  Sync daemon is NOT running")
            
            if questionary.confirm(
                "\nStart sync daemon now?",
                default=True,
                style=AUTOTRAINX_STYLE
            ).ask():
                self._start_sync_daemon()
                
        questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        
    def _configure_security(self):
        """Configure security settings."""
        self.show_header()
        print("\033[1;33m=== SECURITY CONFIGURATION ===\033[0m\n")
        
        env_vars = self._load_env_file()
        
        # API Secret Key
        if 'API_SECRET_KEY' not in env_vars or not env_vars.get('API_SECRET_KEY'):
            if questionary.confirm(
                "Generate new API secret key?",
                default=True,
                style=AUTOTRAINX_STYLE
            ).ask():
                api_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
                env_vars['API_SECRET_KEY'] = api_key
                print("✅ Generated new API secret key")
                
        # JWT Secret Key
        if 'JWT_SECRET_KEY' not in env_vars or not env_vars.get('JWT_SECRET_KEY'):
            if questionary.confirm(
                "\nGenerate new JWT secret key?",
                default=True,
                style=AUTOTRAINX_STYLE
            ).ask():
                jwt_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
                env_vars['JWT_SECRET_KEY'] = jwt_key
                env_vars['JWT_ALGORITHM'] = 'HS256'
                env_vars['JWT_ACCESS_TOKEN_EXPIRE_MINUTES'] = '30'
                print("✅ Generated new JWT secret key")
                
        # CORS Configuration
        if questionary.confirm(
            "\nConfigure CORS settings?",
            default=False,
            style=AUTOTRAINX_STYLE
        ).ask():
            env_vars['CORS_ALLOWED_ORIGINS'] = questionary.text(
                "Allowed origins (* for all):",
                default=env_vars.get('CORS_ALLOWED_ORIGINS', '*'),
                style=AUTOTRAINX_STYLE
            ).ask()
            
            env_vars['CORS_ALLOW_CREDENTIALS'] = questionary.select(
                "Allow credentials:",
                choices=['true', 'false'],
                default=env_vars.get('CORS_ALLOW_CREDENTIALS', 'true'),
                style=AUTOTRAINX_STYLE
            ).ask()
            
            env_vars['CORS_ALLOWED_METHODS'] = questionary.text(
                "Allowed methods:",
                default=env_vars.get('CORS_ALLOWED_METHODS', 'GET,POST,PUT,DELETE,OPTIONS'),
                style=AUTOTRAINX_STYLE
            ).ask()
            
            env_vars['CORS_ALLOWED_HEADERS'] = questionary.text(
                "Allowed headers (* for all):",
                default=env_vars.get('CORS_ALLOWED_HEADERS', '*'),
                style=AUTOTRAINX_STYLE
            ).ask()
        else:
            # Set defaults
            env_vars.setdefault('CORS_ALLOWED_ORIGINS', '*')
            env_vars.setdefault('CORS_ALLOW_CREDENTIALS', 'true')
            env_vars.setdefault('CORS_ALLOWED_METHODS', 'GET,POST,PUT,DELETE,OPTIONS')
            env_vars.setdefault('CORS_ALLOWED_HEADERS', '*')
            
        self._save_env_file(env_vars)
        print("\n✅ Security configuration saved!")
        
        questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        
    def _quick_setup(self):
        """Quick setup wizard for all components."""
        self.show_header()
        print("\033[1;33m=== QUICK SETUP WIZARD ===\033[0m\n")
        
        print("This wizard will guide you through configuring all components.\n")
        
        if questionary.confirm(
            "Configure PostgreSQL?",
            default=True,
            style=AUTOTRAINX_STYLE
        ).ask():
            self._configure_postgresql()
            
        if questionary.confirm(
            "\nConfigure Google Sheets?",
            default=True,
            style=AUTOTRAINX_STYLE
        ).ask():
            self._configure_google_sheets()
            
        if questionary.confirm(
            "\nConfigure Security (API Keys)?",
            default=True,
            style=AUTOTRAINX_STYLE
        ).ask():
            self._configure_security()
            
        if questionary.confirm(
            "\nStart Sync Daemon?",
            default=True,
            style=AUTOTRAINX_STYLE
        ).ask():
            self._start_sync_daemon()
            
        print("\n✅ Quick setup complete!")
        questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
        
    # ==================== Helper Methods ====================
    
    def _check_postgresql_installed(self) -> bool:
        """Check if PostgreSQL is installed."""
        result = subprocess.run(['which', 'psql'], capture_output=True, text=True)
        return result.returncode == 0
        
    def _check_google_sheets_installed(self) -> bool:
        """Check if Google Sheets dependencies are installed."""
        try:
            import google.auth
            import googleapiclient
            return True
        except ImportError:
            return False
            
    def _check_daemon_running(self) -> bool:
        """Check if sync daemon is running."""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'sheets_sync_daemon.py' in str(cmdline):
                    return True
        except:
            pass
        return False
        
    def _start_sync_daemon(self):
        """Start the sync daemon."""
        print("\n🚀 Starting sync daemon...")
        
        cmd = [sys.executable, 'sheets_sync_daemon.py', '--daemon']
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=self.base_path
        )
        
        time.sleep(2)
        
        if self._check_daemon_running():
            print("✅ Sync daemon started successfully!")
        else:
            print("❌ Failed to start sync daemon")
            
    def _restart_sync_daemon(self):
        """Restart the sync daemon."""
        print("\n🔄 Restarting sync daemon...")
        
        # Stop existing daemon
        subprocess.run([sys.executable, 'sheets_sync_daemon.py', '--stop'], 
                      capture_output=True, cwd=self.base_path)
        time.sleep(1)
        
        # Start new daemon
        self._start_sync_daemon()
        
    def _create_postgresql_database(self, db_name: str, db_user: str, db_password: str):
        """Create PostgreSQL database and user."""
        print("\n📦 Creating PostgreSQL database and user...")
        
        try:
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
            
            for sql, desc in [
                (create_user_sql, "Creating user"),
                (create_db_sql, "Creating database"),
                (grant_sql, "Granting privileges")
            ]:
                cmd = ['sudo', '-u', 'postgres', 'psql', '-c', sql]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0 and "already exists" not in result.stderr:
                    print(f"❌ Failed {desc}: {result.stderr}")
                    return False
                    
            print("✅ Database and user created successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create database: {e}")
            return False
            
    def _load_env_file(self) -> Dict[str, str]:
        """Load existing .env file."""
        env_vars = {}
        if self.env_path.exists():
            with open(self.env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip('"\'')
                        env_vars[key] = value
        return env_vars
        
    def _save_env_file(self, env_vars: Dict[str, str]):
        """Save environment variables to .env file."""
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
            
            for group_name, variables in variable_groups.items():
                group_values = [(var, env_vars[var]) for var in variables if var in env_vars]
                if group_values:
                    f.write(f"# {group_name}\n")
                    for key, value in group_values:
                        if "\\n" in value:
                            f.write(f'{key}="{value}"\n')
                        else:
                            f.write(f"{key}={value}\n")
                    f.write("\n")
                    
    def _update_env_variables(self, updates: Dict[str, str]):
        """Update specific environment variables."""
        env_vars = self._load_env_file()
        env_vars.update(updates)
        self._save_env_file(env_vars)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='AutoTrainX Integrations Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  integrations.py                    # Interactive menu
  integrations.py --verify           # Verify all configurations
  integrations.py --install postgres # Install specific component
  integrations.py --config postgres  # Configure specific component
        """
    )
    
    parser.add_argument('--verify', action='store_true', 
                       help='Verify all configurations and exit')
    parser.add_argument('--install', choices=['postgres', 'google', 'daemon', 'all'],
                       help='Install specific component')
    parser.add_argument('--config', choices=['postgres', 'google', 'daemon', 'security', 'all'],
                       help='Configure specific component')
    
    args = parser.parse_args()
    
    # Check if running in correct environment
    venv_path = Path(__file__).parent / "venv" / "bin" / "activate"
    if not venv_path.exists():
        print("\033[93m⚠️  Warning: Virtual environment not found.\033[0m")
        print("Please run setup.sh first to create the environment.\n")
    
    manager = IntegrationsManager()
    
    try:
        if args.verify:
            manager.verify_system()
        elif args.install:
            if args.install == 'postgres':
                manager._install_postgresql()
            elif args.install == 'google':
                manager._install_google_sheets()
            elif args.install == 'daemon':
                manager._install_sync_daemon()
            elif args.install == 'all':
                manager._install_postgresql()
                manager._install_google_sheets()
                manager._install_sync_daemon()
        elif args.config:
            if args.config == 'postgres':
                manager._configure_postgresql()
            elif args.config == 'google':
                manager._configure_google_sheets()
            elif args.config == 'daemon':
                manager._configure_sync_daemon()
            elif args.config == 'security':
                manager._configure_security()
            elif args.config == 'all':
                manager._quick_setup()
        else:
            # Interactive mode
            manager.main_menu()
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n\033[91m❌ Error: {e}\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    main()
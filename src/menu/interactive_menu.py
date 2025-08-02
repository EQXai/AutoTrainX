#!/usr/bin/env python3
"""
AutoTrainX Interactive Configuration Menu

Provides a user-friendly menu system for configuration and management operations.
Training operations should be performed using the CLI interface (main.py).
This menu focuses on system configuration, preset management, and monitoring.
"""

import sys
import os
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

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
    """Interactive menu interface for AutoTrainX."""
    
    def __init__(self):
        """Initialize the menu system."""
        self.base_path = Config.get_default_base_path()
        self.running = True
        
    def run(self) -> None:
        """Main menu loop."""
        self._show_header()
        
        while self.running:
            try:
                os.system('cls' if os.name == 'nt' else 'clear')
                self._show_header()
                choice = questionary.select(
                    "What would you like to do?",
                    choices=[
                        "⚙️  Configuration Management", 
                        "🛠️  System Administration",
                        "📊 Information & Status",
                        "❌ Exit"
                    ],
                    style=AUTOTRAINX_STYLE
                ).ask()
                
                if choice is None:  # User pressed Ctrl+C
                    break
                    
                if "Configuration Management" in choice:
                    self._configuration_menu()
                elif "System Administration" in choice:
                    self._system_admin_menu()
                elif "Information & Status" in choice:
                    self._info_status_menu()
                elif "Exit" in choice:
                    self.running = False
                    
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                self._show_error(f"An error occurred: {str(e)}")
        
        print("\n" + "="*50)
        print("Thank you for using AutoTrainX!")
        print("="*50)
    
    def _show_header(self) -> None:
        """Display the application header."""
        print("\n" + "="*50)
        print("              AUTOTRAINX")
        print("         Interactive Menu v1.0")
        print("="*50)
        print("Navigate with arrow keys, select with Enter")
        print("Press Ctrl+C to exit at any time")
        print("="*50 + "\n")
    
    # Training operations removed - use CLI for training
    # Interactive menu is for configuration only
    
    def _configuration_menu(self) -> None:
        """Configuration management menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            choice = questionary.select(
                "Configuration Management:",
                choices=[
                    "🎨 Preset Management",
                    "📁 Path Configuration", 
                    "🖼️  ComfyUI Configuration",
                    "📊 Google Sheets Sync",
                    "⚙️  Display Settings",
                    "⬅️  Back to Main Menu"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back to Main Menu" in choice:
                break
                
            if "Preset Management" in choice:
                self._preset_management_menu()
            elif "Path Configuration" in choice:
                self._path_configuration_menu()
            elif "ComfyUI Configuration" in choice:
                self._comfyui_configuration_menu()
            elif "Google Sheets Sync" in choice:
                self._google_sheets_sync_menu()
            elif "Display Settings" in choice:
                self._display_settings_menu()
    
    def _system_admin_menu(self) -> None:
        """System administration menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            choice = questionary.select(
                "System Administration:",
                choices=[
                    "🗄️  Database Management",
                    "🧹 Cleanup Operations",
                    "🔧 System Diagnostics",
                    "⬅️  Back to Main Menu"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back to Main Menu" in choice:
                break
                
            if "Database Management" in choice:
                self._database_management_menu()
            elif "Cleanup Operations" in choice:
                self._cleanup_operations_menu()
            elif "System Diagnostics" in choice:
                self._system_diagnostics_menu()
    
    def _info_status_menu(self) -> None:
        """Information and status menu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            choice = questionary.select(
                "Information & Status:",
                choices=[
                    "📊 System Status",
                    "📋 List Available Presets",
                    "📈 Job History",
                    "📄 Job Details",
                    "📊 Database Statistics",
                    "⬅️  Back to Main Menu"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back to Main Menu" in choice:
                break
                
            if "System Status" in choice:
                self._show_system_status()
            elif "List Available Presets" in choice:
                self._list_presets()
            elif "Job History" in choice:
                self._show_job_history()
            elif "Job Details" in choice:
                self._show_job_details()
            elif "Database Statistics" in choice:
                self._show_database_stats()
    
    
    # Preset Management
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
    
    # Path Configuration
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
                    "📁 Set Custom Output Path",
                    "💾 Save Current Configuration as Profile",
                    "📋 List Saved Profiles",
                    "🔄 Switch to Saved Profile",
                    "🗑️  Delete Saved Profile",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
                
            if "Set Custom Output Path" in choice:
                self._set_custom_path()
            elif "Save Current Configuration" in choice:
                self._save_path_profile()
            elif "List Saved Profiles" in choice:
                self._list_path_profiles()
            elif "Switch to Saved Profile" in choice:
                self._switch_to_profile()
            elif "Delete Saved Profile" in choice:
                self._delete_path_profile()
    
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
    
    # ComfyUI Configuration
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
    
    # Google Sheets Sync Configuration
    def _google_sheets_sync_menu(self) -> None:
        """Google Sheets synchronization configuration submenu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            
            # Check current sync status
            try:
                config_data = Config.load_config(self.base_path)
                sync_config = config_data.get('google_sheets_sync', {})
                enabled = sync_config.get('enabled', False)
                spreadsheet_id = sync_config.get('spreadsheet_id', 'Not configured')
                status_text = f"Status: {'Enabled' if enabled else 'Disabled'}"
                if enabled and spreadsheet_id != 'Not configured':
                    status_text += f" | Sheet: {spreadsheet_id[:20]}..."
            except:
                status_text = "Status: Not configured"
            
            choice = questionary.select(
                f"Google Sheets Sync Configuration - {status_text}:",
                choices=[
                    "✅ Enable/Disable Sync",
                    "📝 Configure Spreadsheet ID",
                    "🔑 Setup Authentication",
                    "📦 Install Dependencies",
                    "⚙️  Advanced Settings",
                    "📊 Test Connection",
                    "📈 View Sync Status",
                    "🔄 Manual Full Sync",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
                
            if "Enable/Disable Sync" in choice:
                self._toggle_sheets_sync()
            elif "Configure Spreadsheet ID" in choice:
                self._configure_spreadsheet_id()
            elif "Setup Authentication" in choice:
                self._setup_sheets_authentication()
            elif "Install Dependencies" in choice:
                self._install_sheets_dependencies()
            elif "Advanced Settings" in choice:
                self._sheets_advanced_settings()
            elif "Test Connection" in choice:
                self._test_sheets_connection()
            elif "View Sync Status" in choice:
                self._view_sync_status()
            elif "Manual Full Sync" in choice:
                self._manual_full_sync()
    
    def _toggle_sheets_sync(self) -> None:
        """Enable or disable Google Sheets sync."""
        try:
            config_data = Config.load_config(self.base_path)
            sync_config = config_data.get('google_sheets_sync', {})
            current_state = sync_config.get('enabled', False)
            
            new_state = questionary.confirm(
                f"Google Sheets sync is currently {'enabled' if current_state else 'disabled'}. "
                f"Do you want to {'disable' if current_state else 'enable'} it?",
                default=not current_state,
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if new_state is not None:
                # Update the configuration
                if 'google_sheets_sync' not in config_data:
                    config_data['google_sheets_sync'] = {}
                config_data['google_sheets_sync']['enabled'] = new_state
                
                # Save the configuration
                Config.save_config(config_data, self.base_path)
                
                print("\n" + "="*40)
                print(f"  GOOGLE SHEETS SYNC {'ENABLED' if new_state else 'DISABLED'}")
                print("="*40)
                
                if new_state:
                    print("\nMake sure you have configured:")
                    print("1. Spreadsheet ID")
                    print("2. Authentication credentials")
                    print("\nUse the menu options to complete setup.")
                else:
                    print("\nGoogle Sheets sync has been disabled.")
                
                print("")
                input("Press Enter to continue...")
                
        except Exception as e:
            self._show_error(f"Error toggling sync: {str(e)}")
    
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
            try:
                # Load current config
                config_data = Config.load_config(self.base_path)
                
                # Ensure google_sheets_sync section exists
                if 'google_sheets_sync' not in config_data:
                    config_data['google_sheets_sync'] = {}
                
                # Update spreadsheet ID
                config_data['google_sheets_sync']['spreadsheet_id'] = spreadsheet_id
                
                # Save configuration
                Config.save_config(config_data, self.base_path)
                
                print("\n" + "="*40)
                print("  SPREADSHEET ID CONFIGURED")
                print("="*40)
                print(f"\nSpreadsheet ID set to: {spreadsheet_id}")
                print("\nIMPORTANT: Make sure the sheet is shared with your service account email")
                print("(found in your credentials JSON file)")
                print("")
                input("Press Enter to continue...")
            except Exception as e:
                self._show_error(f"Error saving spreadsheet ID: {str(e)}")
    
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
        
        creds_path = questionary.path(
            "Enter path to credentials.json file:",
            style=AUTOTRAINX_STYLE
        ).ask()
        
        if creds_path:
            try:
                import shutil
                
                # Create settings directory if it doesn't exist
                settings_dir = Path(self.base_path) / "settings"
                settings_dir.mkdir(exist_ok=True)
                
                # Copy credentials file
                dest_path = settings_dir / "google_credentials.json"
                shutil.copy2(creds_path, dest_path)
                
                print(f"\n✅ Credentials copied to: {dest_path}")
                
                # Update configuration
                config_data = Config.load_config(self.base_path)
                if 'google_sheets_sync' not in config_data:
                    config_data['google_sheets_sync'] = {}
                
                config_data['google_sheets_sync']['credentials_path'] = "settings/google_credentials.json"
                
                # If spreadsheet ID is already configured, we're done
                if config_data['google_sheets_sync'].get('spreadsheet_id'):
                    config_data['google_sheets_sync']['enabled'] = True
                    Config.save_config(config_data, self.base_path)
                    print("\n✅ Authentication configured successfully!")
                    print("   Google Sheets sync is now ready to use.")
                    print("\n⚠️  Note: OAuth2 will open a browser for authorization on first use.")
                else:
                    Config.save_config(config_data, self.base_path)
                    print("\n✅ Authentication configured!")
                    print("   Now configure your Spreadsheet ID to complete setup.")
                
                print("")
                input("Press Enter to continue...")
                
            except Exception as e:
                self._show_error(f"Error setting up authentication: {str(e)}")
    
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
                import shutil
                import json
                
                # Create settings directory if it doesn't exist
                settings_dir = Path(self.base_path) / "settings"
                settings_dir.mkdir(exist_ok=True)
                
                # Copy credentials file
                dest_path = settings_dir / "google_credentials.json"
                shutil.copy2(key_path, dest_path)
                
                print(f"\n✅ Credentials copied to: {dest_path}")
                
                # Read service account email
                service_account_email = None
                try:
                    with open(dest_path, 'r') as f:
                        creds_data = json.load(f)
                        service_account_email = creds_data.get('client_email')
                        if service_account_email:
                            print(f"\n📧 Service Account Email: {service_account_email}")
                            print("⚠️  IMPORTANT: Share your Google Sheet with this email!")
                except:
                    pass
                
                # Update configuration
                config_data = Config.load_config(self.base_path)
                if 'google_sheets_sync' not in config_data:
                    config_data['google_sheets_sync'] = {}
                
                config_data['google_sheets_sync']['credentials_path'] = "settings/google_credentials.json"
                
                # If spreadsheet ID is already configured, we're done
                if config_data['google_sheets_sync'].get('spreadsheet_id'):
                    config_data['google_sheets_sync']['enabled'] = True
                    Config.save_config(config_data, self.base_path)
                    print("\n✅ Authentication configured successfully!")
                    print("   Google Sheets sync is now ready to use.")
                else:
                    Config.save_config(config_data, self.base_path)
                    print("\n✅ Authentication configured!")
                    print("   Now configure your Spreadsheet ID to complete setup.")
                
                print("")
                input("Press Enter to continue...")
                
            except Exception as e:
                self._show_error(f"Error setting up authentication: {str(e)}")
    
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
            
            # Check if we're in a virtual environment
            in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
            
            if not in_venv:
                print("\n⚠️  Warning: Not in a virtual environment.")
                print("   It's recommended to use a virtual environment.")
                
                if not questionary.confirm(
                    "Continue anyway?",
                    default=False,
                    style=AUTOTRAINX_STYLE
                ).ask():
                    return
            
            # Build pip command
            pip_cmd = [sys.executable, "-m", "pip", "install",
                      "google-api-python-client",
                      "google-auth",
                      "google-auth-oauthlib",
                      "google-auth-httplib2"]
            
            try:
                import subprocess
                print("\nRunning: " + " ".join(pip_cmd))
                print("-" * 50)
                
                result = subprocess.run(pip_cmd, capture_output=False, text=True)
                
                if result.returncode == 0:
                    print("-" * 50)
                    print("\n✅ Dependencies installed successfully!")
                    print("   You can now use the Google Sheets sync features.")
                else:
                    print("-" * 50)
                    print(f"\n❌ Installation failed with exit code {result.returncode}")
                    print("   Please try installing manually:")
                    print("   pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2")
                    
            except Exception as e:
                print(f"\n❌ Error installing dependencies: {e}")
                print("   Please try installing manually:")
                print("   pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2")
            
            input("\nPress Enter to continue...")
    
    def _sheets_advanced_settings(self) -> None:
        """Configure advanced Google Sheets sync settings."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            choice = questionary.select(
                "Advanced Google Sheets Settings:",
                choices=[
                    "⏱️  Sync Interval (seconds)",
                    "📦 Batch Size",
                    "🔄 Retry Settings",
                    "🚀 Real-time Events",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
                
            if "Sync Interval" in choice:
                interval = questionary.text(
                    "Enter sync interval in seconds (default: 30):",
                    default="30",
                    style=AUTOTRAINX_STYLE
                ).ask()
                if interval:
                    cmd = ["python", "main.py", "--configure", "--sheets-interval", interval]
                    self._execute_command(cmd, "Setting sync interval")
                    
            elif "Batch Size" in choice:
                batch_size = questionary.text(
                    "Enter batch size (default: 50):",
                    default="50",
                    style=AUTOTRAINX_STYLE
                ).ask()
                if batch_size:
                    cmd = ["python", "main.py", "--configure", "--sheets-batch-size", batch_size]
                    self._execute_command(cmd, "Setting batch size")
                    
            elif "Retry Settings" in choice:
                max_retries = questionary.text(
                    "Enter maximum retry attempts (default: 3):",
                    default="3",
                    style=AUTOTRAINX_STYLE
                ).ask()
                if max_retries:
                    cmd = ["python", "main.py", "--configure", "--sheets-retries", max_retries]
                    self._execute_command(cmd, "Setting retry attempts")
                    
            elif "Real-time Events" in choice:
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
                    cmd = ["python", "main.py", "--configure", "--sheets-realtime-events"] + events
                    self._execute_command(cmd, "Configuring real-time events")
    
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
            
            credentials_path = sync_config.get('credentials_path', 'settings/google_credentials.json')
            if not Path(credentials_path).exists():
                print(f"\n❌ Credentials file not found: {credentials_path}")
                print("   Please set up authentication first.")
                input("\nPress Enter to continue...")
                return
            
            print("\nConfiguration found:")
            print(f"  - Spreadsheet ID: {spreadsheet_id}")
            print(f"  - Credentials: {credentials_path}")
            print("\nTesting connection...")
            
            # Import and run the test
            try:
                import asyncio
                import sys
                
                # Add project root to path
                project_root = Path(__file__).parent.parent.parent
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                
                from src.sheets_sync.integration import test_connection
                
                # Run the async test
                result = asyncio.run(test_connection())
                
                if result:
                    print("\n✅ Connection test successful!")
                    print("   Google Sheets API is working correctly.")
                    print("   Your credentials are valid.")
                    print("   The spreadsheet is accessible.")
                else:
                    print("\n❌ Connection test failed!")
                    
                    # Check for specific error messages
                    if "SERVICE_DISABLED" in str(e) or "has not been used" in str(e):
                        print("\n⚠️  GOOGLE SHEETS API IS NOT ENABLED!")
                        print("\nTo fix this:")
                        print("1. Go to: https://console.developers.google.com/apis/api/sheets.googleapis.com/overview")
                        print("2. Click 'ENABLE' button")
                        print("3. Wait 1-2 minutes for changes to propagate")
                        print("4. Try again")
                    elif "403" in str(e) and "permission" in str(e).lower():
                        print("\n⚠️  PERMISSION DENIED!")
                        print("\nMake sure your Google Sheet is shared with the service account email.")
                        print("Check the credentials file for the correct email address.")
                    else:
                        print("\nPossible issues:")
                        print("  - The credentials file is invalid or corrupted")
                        print("  - The spreadsheet ID doesn't exist")
                        print("  - The spreadsheet is not shared with the service account")
                        print("  - No internet connection")
                    
                    # Try to get more details
                    try:
                        # Run a separate async function to get details
                        async def get_error_details():
                            from src.sheets_sync.integration import AutoTrainXSheetsIntegration
                            from src.sheets_sync.service import SheetsSyncService
                            integration = AutoTrainXSheetsIntegration(self.base_path)
                            integration.service = SheetsSyncService(self.base_path)
                            await integration.service.initialize()
                            return await integration.test_connection()
                        
                        detailed_result = asyncio.run(get_error_details())
                        if 'message' in detailed_result:
                            print(f"\nDetailed error: {detailed_result['message']}")
                    except Exception as detail_error:
                        pass  # Silently ignore detail errors
                    
            except ImportError as e:
                print(f"\n❌ Import error: {e}")
                
                # Check if it's a Google API import error
                if "googleapiclient" in str(e) or "google" in str(e):
                    print("\n📦 Missing Google Sheets API dependencies!")
                    print("\nTo install the required dependencies, run:")
                    print("\n   pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2")
                    print("\nOr if using a virtual environment:")
                    print("   source venv/bin/activate  # Activate your venv first")
                    print("   pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2")
                    print("\nAlternatively, run the installation script:")
                    print("   ./install_sheets_deps.sh")
                else:
                    print("\n⚠️  Module import error - this might be a code issue.")
                    print("\nMake sure you're running from the AutoTrainX directory.")
                    print("If using a virtual environment, make sure it's activated:")
                    print("\n   source venv/bin/activate")
                    print("   python src/menu/interactive_menu.py")
            except Exception as e:
                print(f"\n❌ Connection test failed: {e}")
                print("\nPossible issues:")
                print("  - Invalid credentials")
                print("  - Spreadsheet not shared with service account")
                print("  - No internet connection")
                print("  - Google Sheets API not enabled")
                
        except Exception as e:
            print(f"\n❌ Error during test: {e}")
        
        input("\nPress Enter to continue...")
    
    def _view_sync_status(self) -> None:
        """View current sync status and statistics."""
        print("\n" + "="*40)
        print("  SYNC STATUS")
        print("="*40)
        try:
            config_data = Config.load_config(self.base_path)
            sync_config = config_data.get('google_sheets_sync', {})
            enabled = sync_config.get('enabled', False)
            spreadsheet_id = sync_config.get('spreadsheet_id', 'Not configured')
            
            print(f"\nSync Enabled: {enabled}")
            print(f"Spreadsheet ID: {spreadsheet_id}")
            print(f"Credentials Path: {sync_config.get('credentials_path', 'Not configured')}")
            print("\nSync Settings:")
            settings = sync_config.get('sync_settings', {})
            print(f"  - Batch Size: {settings.get('batch_size', 50)}")
            print(f"  - Sync Interval: {settings.get('batch_interval_seconds', 30)}s")
            print(f"  - Max Retries: {settings.get('max_retry_attempts', 3)}")
            print(f"  - Real-time Events: {', '.join(settings.get('realtime_events', []))}")
        except Exception as e:
            print(f"Error reading configuration: {e}")
        print("")
        input("Press Enter to continue...")
    
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
                    import sys
                    
                    # Add project root to path
                    project_root = Path(__file__).parent.parent.parent
                    if str(project_root) not in sys.path:
                        sys.path.insert(0, str(project_root))
                    
                    from src.sheets_sync.integration import manual_full_sync
                    
                    # Run the async sync
                    result = asyncio.run(manual_full_sync())
                    
                    if result.success:
                        print(f"\n✅ Synchronization completed successfully!")
                        print(f"   {result.message}")
                        if result.data:
                            print(f"   Total records synced: {result.data.get('total_synced', 0)}")
                            print(f"   Executions: {result.data.get('executions_synced', 0)}")
                            print(f"   Variations: {result.data.get('variations_synced', 0)}")
                    else:
                        print(f"\n❌ Synchronization failed: {result.message}")
                        
                except ImportError as e:
                    print(f"\n❌ Import error: {e}")
                    print("\n📦 Missing Google Sheets API dependencies!")
                    print("\nTo install the required dependencies, run:")
                    print("\n   pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2")
                    print("\nOr if using a virtual environment:")
                    print("   source venv/bin/activate  # Activate your venv first")
                    print("   pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2")
                    print("\nAlternatively, run the installation script:")
                    print("   ./install_sheets_deps.sh")
                except Exception as e:
                    print(f"\n❌ Synchronization failed: {e}")
                    
            except Exception as e:
                print(f"\n❌ Error during sync: {e}")
            
            input("\nPress Enter to continue...")
    
    # Display Settings
    def _display_settings_menu(self) -> None:
        """Display settings submenu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            choice = questionary.select(
                "Display Settings:",
                choices=[
                    "📊 Set Progress Display Mode",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
                
            if "Set Progress Display Mode" in choice:
                self._set_progress_display()
    
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
    
    # Database Management
    def _database_management_menu(self) -> None:
        """Database management submenu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            choice = questionary.select(
                "Database Management:",
                choices=[
                    "📊 Database Statistics",
                    "🗑️  Clear All Records",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
                
            if "Database Statistics" in choice:
                self._show_database_stats()
            elif "Clear All Records" in choice:
                self._clear_database()
    
    def _clear_database(self) -> None:
        """Clear all database records."""
        if questionary.confirm(
            "This will permanently delete ALL training records. Are you sure?",
            default=False,
            style=AUTOTRAINX_STYLE
        ).ask():
            cmd = ["python", "main.py", "--clear-db"]
            self._execute_command(cmd, "Clearing database")
    
    # Cleanup Operations
    def _cleanup_operations_menu(self) -> None:
        """Cleanup operations submenu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            choice = questionary.select(
                "Cleanup Operations:",
                choices=[
                    "🧹 Cleanup Stale Processes",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
                
            if "Cleanup Stale Processes" in choice:
                self._cleanup_stale_processes()
    
    def _cleanup_stale_processes(self) -> None:
        """Clean up stale processes."""
        cmd = ["python", "main.py", "--cleanup-stale"]
        self._execute_command(cmd, "Cleaning up stale processes")
    
    # System Diagnostics
    def _system_diagnostics_menu(self) -> None:
        """System diagnostics submenu."""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            self._show_header()
            choice = questionary.select(
                "System Diagnostics:",
                choices=[
                    "📊 System Status",
                    "🔍 ComfyUI Diagnosis",
                    "✅ Preview System Validation",
                    "⬅️  Back"
                ],
                style=AUTOTRAINX_STYLE
            ).ask()
            
            if choice is None or "Back" in choice:
                break
                
            if "System Status" in choice:
                self._show_system_status()
            elif "ComfyUI Diagnosis" in choice:
                self._diagnose_comfyui()
            elif "Preview System Validation" in choice:
                self._validate_preview_system()
    
    # Information Display Methods
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
    
    def _show_database_stats(self) -> None:
        """Show database statistics."""
        cmd = ["python", "main.py", "--db-stats"]
        self._execute_command(cmd, "Database Statistics")
    
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
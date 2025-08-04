#!/usr/bin/env python3
"""
AutoTrainX Main CLI - Simplified version using unified argument system.

This script provides a clean, intuitive interface for the AutoTrainX pipeline.

Usage examples:
    # Launch interactive menu
    python main.py --menu
    
    # Train single dataset
    python main.py --train --single --source /home/eqx/datasets/3/dl4r0s4 --preset FluxLORA
    
    # Train batch of datasets
    python main.py --train --batch --source /home/eqx/datasets/3 --preset FluxLORA
    
    # Train with variations
    python main.py --train --mode variations --source b09g13 --preset FluxLORA \
           --variations network_dim=32,64,128 network_alpha=16,32
    
    # Just prepare dataset
    python main.py --prepare --single --source /home/eqx/datasets/1/b09g13
    
    # Show status
    python main.py --status
"""

# IMPORTANT: Load environment variables FIRST before any other imports
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Try to load .env from various locations (prioritize root .env)
project_root = Path(__file__).parent
env_paths = [
    project_root / '.env',  # Root .env first
    project_root / 'settings' / '.env',  # Settings .env as fallback
]

env_loaded = False
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path, override=True)  # Force override existing variables
        print(f"Loaded environment from: {env_path}")
        env_loaded = True
        break

if not env_loaded:
    print("Warning: No .env file found")

# Set PostgreSQL configuration with defaults (but allow env override)
if 'DATABASE_TYPE' not in os.environ:
    os.environ['DATABASE_TYPE'] = 'postgresql'
if 'DATABASE_HOST' not in os.environ:
    os.environ['DATABASE_HOST'] = 'localhost'
if 'DATABASE_PORT' not in os.environ:
    os.environ['DATABASE_PORT'] = '5432'
if 'DATABASE_NAME' not in os.environ:
    os.environ['DATABASE_NAME'] = 'autotrainx'
if 'DATABASE_USER' not in os.environ:
    os.environ['DATABASE_USER'] = 'autotrainx'
if 'DATABASE_PASSWORD' not in os.environ:
    os.environ['DATABASE_PASSWORD'] = '1234'  # Default only if not set

# Now import other standard library modules
import json
import asyncio

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Reload database settings after environment is loaded
from src.database.config import reload_db_settings
reload_db_settings()

from src.pipeline.pipeline import AutoTrainPipeline
from src.pipeline.base import PipelineConfig
from src.scripts.models import verify_all_models
from src.cli import UnifiedArgumentParser, UnifiedCommandHandler, ResultFormatter
from src.cli.unified_args import Operation
from src.utils.logging_config import setup_logging, get_logger
from src.utils.workspace_setup import WorkspaceSetup
from src.utils.display import DisplayBox
from src.utils.signal_handler import get_shutdown_handler
from src.utils.path_manager import PathManager, PathProfile
from src.config import Config
# from src.sheets_sync.start_watcher import start_integrated_watcher, stop_integrated_watcher
# Commented out: daemon runs independently now


async def async_main():
    """Async main entry point with simplified argument handling."""
    # Register signal handler for graceful shutdown
    shutdown_handler = get_shutdown_handler()
    shutdown_handler.register()
    
    # Initialize Google Sheets sync service if enabled
    watcher_started = False
    try:
        config_data = Config.load_config()
        if config_data.get('google_sheets_sync', {}).get('enabled', False):
            logger_temp = get_logger(__name__)
            
            # Note: Sheets sync daemon runs independently now
            logger_temp.info("Google Sheets sync is enabled. Run daemon separately with:")
            logger_temp.info("  python sheets_sync_daemon.py --daemon")
    except Exception as e:
        pass  # Silently fail if sync service has issues
    
    # Parse arguments using unified system
    try:
        args = UnifiedArgumentParser.parse_args()
    except ValueError as e:
        print(f"Error: {e}")
        shutdown_handler.unregister()
        return 1
    
    # Validate arguments
    validation_error = UnifiedArgumentParser.validate_args(args)
    if validation_error:
        print(f"Error: {validation_error}")
        shutdown_handler.unregister()
        return 1
    
    # Initialize variables
    init_info = None
    logger = None
    
    # Only setup logging for operations that need it (training, preparation)
    if args.operation.value in ['train', 'prepare']:
        # Temporarily suppress console output during setup
        setup_logging(
            console=False,  # Temporarily disable console
            file=True,
            base_path=args.base_path
        )
        logger = get_logger(__name__)
        
        # Get logging info for display
        from src.utils.logging_config import get_logging_manager
        log_manager = get_logging_manager(args.base_path)
        
        # Store initialization info for later display
        init_info = {
            "log_level": "INFO",
            "execution_id": log_manager.execution_id,
            "log_file": str(log_manager.execution_log)
        }
        
        # Re-enable console logging after initialization display
        setup_logging(
            console=not args.json,
            file=True,
            base_path=args.base_path
        )
    
    try:
        # Handle menu operation first
        if args.operation == Operation.MENU:
            # Launch interactive menu
            import subprocess
            menu_script = Path(__file__).parent / "src" / "menu" / "interactive_menu.py"
            
            if not menu_script.exists():
                print("Error: Interactive menu script not found")
                return 1
            
            # Clear screen and show header
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print("\033[1;36m" + "╔" + "═" * 58 + "╗" + "\033[0m")
            print("\033[1;36m║" + " " * 15 + "AutoTrainX Menu Session" + " " * 20 + "║\033[0m")
            print("\033[1;36m╚" + "═" * 58 + "╝" + "\033[0m")
            
            try:
                # Try to import questionary to check if it's installed
                import questionary
            except ImportError:
                print("\nInstalling required dependencies...")
                requirements_file = Path(__file__).parent / "src" / "menu" / "interactive_menu_requirements.txt"
                if requirements_file.exists():
                    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])
                else:
                    subprocess.run([sys.executable, "-m", "pip", "install", "questionary>=2.0.0"])
            
            try:
                # Launch the interactive menu with proper terminal handling
                result = subprocess.run(
                    [sys.executable, str(menu_script)],
                    stdin=sys.stdin,
                    stdout=sys.stdout,
                    stderr=sys.stderr
                )
                exit_code = result.returncode
            except KeyboardInterrupt:
                print("\n\n\033[0;33m✗ Menu session interrupted\033[0m")
                exit_code = 130
            except Exception as e:
                print(f"\n\033[0;31m✗ Error: {e}\033[0m")
                exit_code = 1
            
            # Show return message
            print("\n\033[1;36m" + "─" * 60 + "\033[0m")
            print("\033[1;32m✓ Returned to normal terminal\033[0m")
            print("\033[1;36m" + "═" * 60 + "\033[0m")
            
            shutdown_handler.unregister()
            return exit_code
        
        # Handle ComfyUI path if provided
        if args.comfyui_path:
            Config.set_comfyui_path(args.comfyui_path, args.base_path)
            
        # Handle progress display setting if provided
        if hasattr(args, 'set_progress_display') and args.set_progress_display:
            show_progress = args.set_progress_display == 'progress'
            Config.set_training_progress_setting(show_progress, args.base_path)
            # Exit after setting config
            return 0
        
        # Handle custom path configuration
        custom_output_path = None
        profile_manager = PathProfile(base_path=args.base_path)
        profile_to_use = None
        
        # Priority 1: Check if using a profile from command line
        if args.use_profile:
            profile = profile_manager.get_profile(args.use_profile)
            if not profile:
                print(f"Error: Profile '{args.use_profile}' not found")
                return 1
            profile_to_use = args.use_profile
            custom_output_path = profile.get('custom_output_path')
            # Save as active profile for future use
            Config.set_active_profile(args.use_profile, args.base_path)
        else:
            # Priority 2: Use the saved active profile
            active_profile = Config.get_active_profile(args.base_path)
            if active_profile:
                profile = profile_manager.get_profile(active_profile)
                if profile:
                    profile_to_use = active_profile
                    custom_output_path = profile.get('custom_output_path')
        
        # Priority 3: Override with command-line custom path if provided
        if args.custom_path:
            custom_output_path = args.custom_path
            # Note: This doesn't change the active profile
        
        # Create PathManager instance
        path_manager = PathManager(args.base_path, custom_output_path)
        
        # Display initialization in corporate style if not JSON output and init_info is available
        if not args.json and init_info:
            # Print header
            print(DisplayBox.create_corporate_header("AUTOTRAINX", "v1.0.0"))
            
            # System initialization section
            init_content = {
                "Logging Level": init_info["log_level"],
                "Execution ID": init_info["execution_id"],
                "Log File": init_info["log_file"]
            }
            
            # Add custom path info if applicable
            if custom_output_path:
                init_content["Output Path"] = f"CUSTOM: {custom_output_path}"
            else:
                init_content["Output Path"] = "DEFAULT: workspace/output"
                
            print(DisplayBox.create_corporate_section("SYSTEM INITIALIZATION", init_content))
        
        # Create pipeline configuration
        config = PipelineConfig(
            base_path=args.base_path,
            auto_clean=args.auto_clean,
            parallel=args.parallel,
            verbose=not args.json,
            path_manager=path_manager
        )
        
        # Validate and setup workspace
        workspace_validation = WorkspaceSetup.validate_workspace(args.base_path)
        if not workspace_validation["valid"]:
            if not args.json:
                print("🔧 Setting up workspace structure...")
            
            if WorkspaceSetup.setup_workspace(args.base_path):
                if not args.json:
                    print("✓ Workspace structure created successfully.")
            else:
                error_msg = "Failed to setup workspace structure."
                if args.json:
                    print(json.dumps({"success": False, "error": error_msg}, indent=2))
                else:
                    print(f"Error: {error_msg}")
                return 1
        
        # Initialize pipeline
        pipeline = AutoTrainPipeline(args.base_path, config)
        
        # Configure preview generation if requested
        if args.preview and args.preview > 0:
            # This will be passed to hooks through context
            config.preview_count = args.preview
        
        # Initialize formatter
        formatter = ResultFormatter(json_output=args.json)
        
        # Initialize unified command handler
        handler = UnifiedCommandHandler(pipeline, formatter)
        
        # Verify models if needed
        if args.operation.value in ['train', 'prepare']:
            if not args.json:
                # Capture model verification output
                import io
                import contextlib
                
                # Redirect stdout to capture model verification messages
                captured_output = io.StringIO()
                with contextlib.redirect_stdout(captured_output):
                    models_verified = verify_all_models()
                
                # Get the output and parse it
                model_output = captured_output.getvalue()
                model_lines = [line.strip() for line in model_output.strip().split('\n') if line.strip()]
                
                # Display model verification in corporate style
                if model_lines:
                    # Parse the model verification output
                    model_status = "PASSED"
                    models_found = "Unknown"
                    result_msg = "Unknown"
                    
                    for line in model_lines:
                        if "All" in line and "required models" in line:
                            # Extract number of models from the message, ignoring timestamp
                            import re
                            # Remove timestamp and INFO tag first
                            clean_line = re.sub(r'\[.*?\]', '', line).strip()
                            clean_line = clean_line.replace('[INFO]', '').strip()
                            # Now extract numbers from the clean message
                            numbers = re.findall(r'\d+', clean_line)
                            if numbers:
                                models_found = f"{numbers[0]}/{numbers[0]}"
                            result_msg = "All required models verified successfully"
                        elif "missing" in line:
                            model_status = "FAILED"
                            result_msg = line
                    
                    model_content = {
                        "Status": model_status,
                        "Models Found": models_found,
                        "Result": result_msg
                    }
                    print(DisplayBox.create_corporate_section("MODEL VERIFICATION", model_content))
                    
                    # Print footer
                    print(DisplayBox.create_corporate_footer())
                    print()  # Add spacing
                
                if not models_verified:
                    error_msg = "Model verification failed. Please check your model directory."
                    print(f"Error: {error_msg}")
                    return 1
            else:
                if not verify_all_models():
                    error_msg = "Model verification failed. Please check your model directory."
                    print(json.dumps({"success": False, "error": error_msg}, indent=2))
                    return 1
        
        # Execute command
        result = handler.execute(args)
        
        # Stop sync service if it was started
        if watcher_started:
            try:
                # Daemon runs independently now
                pass
                if logger:
                    logger.info("Database watcher stopped")
            except Exception:
                pass  # Silently fail
        
        # Unregister handler on successful completion
        shutdown_handler.unregister()
        return result
        
    except KeyboardInterrupt:
        # This should not normally be reached due to signal handler
        # but kept as fallback
        
        # Stop sync service if it was started
        if watcher_started:
            try:
                # Daemon runs independently now
                pass
            except Exception:
                pass
                
        shutdown_handler.unregister()
        if args.json:
            print(json.dumps({"success": False, "error": "Operation cancelled"}, indent=2))
        else:
            print("\nOperation cancelled by user")
        return 1
        
    except Exception as e:
        # Stop sync service if it was started
        if watcher_started:
            try:
                # Daemon runs independently now
                pass
            except Exception:
                pass
                
        shutdown_handler.unregister()
        error_msg = f"Unexpected error: {str(e)}"
        if args.json:
            print(json.dumps({"success": False, "error": str(e)}, indent=2))
        else:
            print(f"Error: {error_msg}")
            if logger:
                logger.exception("Unexpected error occurred")
        return 1


def main():
    """Synchronous wrapper for async main."""
    return asyncio.run(async_main())


if __name__ == "__main__":
    exit(main())
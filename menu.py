#!/usr/bin/env python3
"""
AutoTrainX Menu Launcher

Launches the interactive menu interface in an isolated terminal session.
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    """Launch the interactive menu with terminal isolation."""
    menu_script = Path(__file__).parent / "src" / "menu" / "interactive_menu.py"
    
    if not menu_script.exists():
        print("Error: interactive_menu.py not found")
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
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
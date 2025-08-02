#!/usr/bin/env python3
"""
Subprocess wrapper to isolate training processes from terminal signals.

This wrapper ensures that the training subprocess doesn't receive SIGINT
when the user presses Ctrl+C in the parent process.
"""

import os
import sys
import signal
import subprocess


def signal_handler(signum, frame):
    """Ignore SIGINT signals."""
    pass


def main():
    """Run the actual command with signal isolation."""
    # Ignore SIGINT
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    # Get command from arguments
    if len(sys.argv) < 2:
        print("Error: No command provided to wrapper")
        sys.exit(1)
    
    # Execute the actual command
    command = sys.argv[1:]
    
    try:
        # Run the command and pass through all output
        process = subprocess.run(command, check=False)
        sys.exit(process.returncode)
    except Exception as e:
        print(f"Wrapper error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
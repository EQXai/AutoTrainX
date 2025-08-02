#!/usr/bin/env python3
"""
Google Sheets Sync Daemon for AutoTrainX

This daemon monitors the database for changes and automatically synchronizes
with Google Sheets. It runs independently of the main AutoTrainX process.

Usage:
    python sheets_sync_daemon.py            # Run in foreground
    python sheets_sync_daemon.py --daemon   # Run as daemon (background)
    python sheets_sync_daemon.py --stop     # Stop daemon
    python sheets_sync_daemon.py --status   # Check daemon status
"""

import sys
import os
import asyncio
import argparse
import logging
import signal
import json
from pathlib import Path
from typing import Optional
import psutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.sheets_sync.db_watcher import DatabaseWatcherService
from src.config import Config

# PID file location
PID_FILE = Path(__file__).parent / ".sheets_sync_daemon.pid"
LOG_FILE = Path(__file__).parent / "logs" / "sheets_sync_daemon.log"


def setup_logging(log_file: Path, daemon: bool = False):
    """Setup logging configuration."""
    log_file.parent.mkdir(exist_ok=True)
    
    # Configure logging
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    if daemon:
        # Log only to file in daemon mode
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
            ]
        )
    else:
        # Log to both console and file in foreground mode
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_file),
            ]
        )


def is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running."""
    try:
        process = psutil.Process(pid)
        return process.is_running()
    except psutil.NoSuchProcess:
        return False


def get_daemon_pid() -> Optional[int]:
    """Get the PID of the running daemon."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if is_process_running(pid):
                return pid
            else:
                # PID file exists but process is not running
                PID_FILE.unlink()
        except (ValueError, OSError):
            pass
    return None


def daemonize():
    """Daemonize the current process."""
    # Save current working directory before daemonizing
    original_cwd = os.getcwd()
    
    # First fork
    try:
        pid = os.fork()
        if pid > 0:
            # Exit parent process
            sys.exit(0)
    except OSError as e:
        print(f"Fork #1 failed: {e}")
        sys.exit(1)
    
    # Decouple from parent environment
    os.chdir(original_cwd)  # Keep original working directory instead of "/"
    os.setsid()
    os.umask(0)
    
    # Second fork
    try:
        pid = os.fork()
        if pid > 0:
            # Exit from second parent
            sys.exit(0)
    except OSError as e:
        print(f"Fork #2 failed: {e}")
        sys.exit(1)
    
    # Redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    
    # Close file descriptors
    null = os.open(os.devnull, os.O_RDWR)
    os.dup2(null, sys.stdin.fileno())
    os.dup2(null, sys.stdout.fileno())
    os.dup2(null, sys.stderr.fileno())
    os.close(null)


async def run_service():
    """Run the database watcher service."""
    logger = logging.getLogger(__name__)
    
    # Check if Google Sheets sync is enabled
    config = Config.load_config()
    if not config.get('google_sheets_sync', {}).get('enabled', False):
        logger.error("Google Sheets sync is disabled in config.json")
        return 1
    
    # Create and start service
    service = DatabaseWatcherService()
    
    # Handle shutdown signals
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the service
        await service.start()
        logger.info("Database watcher service started successfully")
        
        # Save PID
        PID_FILE.write_text(str(os.getpid()))
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        
        # Stop service
        await service.stop()
        logger.info("Database watcher service stopped")
        
    except Exception as e:
        logger.error(f"Service error: {e}", exc_info=True)
        return 1
    finally:
        # Clean up PID file
        if PID_FILE.exists():
            PID_FILE.unlink()
    
    return 0


def start_daemon():
    """Start the daemon."""
    # Check if already running
    pid = get_daemon_pid()
    if pid:
        print(f"Daemon is already running (PID: {pid})")
        return 1
    
    # Check if Google Sheets sync is enabled
    config = Config.load_config()
    if not config.get('google_sheets_sync', {}).get('enabled', False):
        print("Error: Google Sheets sync is disabled in config.json")
        print("Enable it first by setting google_sheets_sync.enabled to true")
        return 1
    
    print("Starting Google Sheets sync daemon...")
    
    # Daemonize
    daemonize()
    
    # Setup logging for daemon
    setup_logging(LOG_FILE, daemon=True)
    
    # Run the service
    return asyncio.run(run_service())


def stop_daemon():
    """Stop the daemon."""
    pid = get_daemon_pid()
    if not pid:
        print("Daemon is not running")
        return 1
    
    print(f"Stopping daemon (PID: {pid})...")
    
    try:
        os.kill(pid, signal.SIGTERM)
        print("Daemon stopped successfully")
        return 0
    except ProcessLookupError:
        print("Daemon process not found")
        if PID_FILE.exists():
            PID_FILE.unlink()
        return 1
    except Exception as e:
        print(f"Error stopping daemon: {e}")
        return 1


def check_status():
    """Check daemon status."""
    pid = get_daemon_pid()
    
    if pid:
        print(f"✓ Google Sheets sync daemon is running (PID: {pid})")
        
        # Check log file for recent activity
        if LOG_FILE.exists():
            import datetime
            mod_time = datetime.datetime.fromtimestamp(LOG_FILE.stat().st_mtime)
            print(f"  Last log activity: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Show last few log lines
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()
                if lines:
                    print("\n  Recent log entries:")
                    for line in lines[-5:]:
                        print(f"    {line.strip()}")
    else:
        print("✗ Google Sheets sync daemon is not running")
    
    # Check configuration
    config = Config.load_config()
    sheets_config = config.get('google_sheets_sync', {})
    
    print(f"\nConfiguration:")
    print(f"  Enabled: {sheets_config.get('enabled', False)}")
    print(f"  Spreadsheet ID: {sheets_config.get('spreadsheet_id', 'Not configured')}")
    
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Google Sheets Sync Daemon for AutoTrainX",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--daemon', '-d',
        action='store_true',
        help='Run as daemon (background process)'
    )
    
    parser.add_argument(
        '--stop',
        action='store_true',
        help='Stop the running daemon'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Check daemon status'
    )
    
    parser.add_argument(
        '--log-file',
        type=Path,
        default=LOG_FILE,
        help='Log file path'
    )
    
    args = parser.parse_args()
    
    # Handle commands
    if args.stop:
        return stop_daemon()
    elif args.status:
        return check_status()
    elif args.daemon:
        return start_daemon()
    else:
        # Run in foreground
        print("Running Google Sheets sync in foreground mode...")
        print("Press Ctrl+C to stop")
        print(f"Logs are being written to: {args.log_file}")
        print()
        
        setup_logging(args.log_file, daemon=False)
        return asyncio.run(run_service())


if __name__ == "__main__":
    sys.exit(main())
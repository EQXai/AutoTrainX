#!/bin/bash
# Start Google Sheets Sync Daemon with PostgreSQL

# Configure PostgreSQL environment
export AUTOTRAINX_DB_TYPE=postgresql
export AUTOTRAINX_DB_HOST=localhost
export AUTOTRAINX_DB_PORT=5432
export AUTOTRAINX_DB_NAME=autotrainx
export AUTOTRAINX_DB_USER=autotrainx
export AUTOTRAINX_DB_PASSWORD=1234

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_FILE="$SCRIPT_DIR/sheets_sync.pid"
LOG_FILE="$SCRIPT_DIR/logs/sheets_sync_daemon.log"

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

echo -e "${GREEN}Starting Google Sheets Sync with PostgreSQL...${NC}"
echo -e "${YELLOW}Database: PostgreSQL @ $AUTOTRAINX_DB_HOST:$AUTOTRAINX_DB_PORT/$AUTOTRAINX_DB_NAME${NC}"

# Function to check if process is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi
    return 1
}

# Function to start in background
start_background() {
    if is_running; then
        echo -e "${YELLOW}⚠️  Sheets sync daemon is already running (PID: $(cat $PID_FILE))${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Starting in background mode...${NC}"
    
    # Start the daemon in background
    nohup python "$SCRIPT_DIR/sheets_sync_daemon_postgresql.py" >> "$LOG_FILE" 2>&1 &
    PID=$!
    
    # Save PID
    echo $PID > "$PID_FILE"
    
    # Wait a moment to check if it started successfully
    sleep 2
    
    if is_running; then
        echo -e "${GREEN}✅ Sheets sync daemon started successfully (PID: $PID)${NC}"
        echo -e "${BLUE}📋 Logs: tail -f $LOG_FILE${NC}"
        echo -e "${BLUE}🛑 To stop: $0 --stop${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to start sheets sync daemon${NC}"
        echo -e "${YELLOW}Check logs: $LOG_FILE${NC}"
        return 1
    fi
}

# Function to stop the daemon
stop_daemon() {
    if ! is_running; then
        echo -e "${YELLOW}⚠️  Sheets sync daemon is not running${NC}"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    echo -e "${BLUE}Stopping sheets sync daemon (PID: $PID)...${NC}"
    
    kill $PID 2>/dev/null
    
    # Wait for process to stop
    for i in {1..10}; do
        if ! ps -p $PID > /dev/null 2>&1; then
            rm -f "$PID_FILE"
            echo -e "${GREEN}✅ Sheets sync daemon stopped${NC}"
            return 0
        fi
        sleep 1
    done
    
    # Force kill if still running
    kill -9 $PID 2>/dev/null
    rm -f "$PID_FILE"
    echo -e "${GREEN}✅ Sheets sync daemon stopped (forced)${NC}"
    return 0
}

# Function to show status
show_status() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        echo -e "${GREEN}✅ Sheets sync daemon is running (PID: $PID)${NC}"
        echo -e "${BLUE}📋 Recent logs:${NC}"
        tail -5 "$LOG_FILE" 2>/dev/null || echo "No logs available"
    else
        echo -e "${YELLOW}⚠️  Sheets sync daemon is not running${NC}"
    fi
}

# Parse command line arguments
case "$1" in
    --background|-b)
        start_background
        ;;
    --stop|-s)
        stop_daemon
        ;;
    --status)
        show_status
        ;;
    --restart|-r)
        stop_daemon
        sleep 1
        start_background
        ;;
    --logs|-l)
        echo -e "${BLUE}📋 Showing logs (Ctrl+C to exit):${NC}"
        tail -f "$LOG_FILE"
        ;;
    --help|-h)
        echo "Usage: $0 [OPTION]"
        echo "Options:"
        echo "  --background, -b    Start daemon in background"
        echo "  --stop, -s         Stop the daemon"
        echo "  --status          Show daemon status"
        echo "  --restart, -r     Restart the daemon"
        echo "  --logs, -l        Show logs (tail -f)"
        echo "  --help, -h        Show this help"
        echo "  (no option)       Start in foreground mode"
        ;;
    "")
        # Default: run in foreground
        echo "Starting in foreground mode (Ctrl+C to stop)..."
        echo -e "${BLUE}💡 Tip: Use '$0 --background' to run in background${NC}"
        python "$SCRIPT_DIR/sheets_sync_daemon_postgresql.py"
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        echo "Use '$0 --help' for usage information"
        exit 1
        ;;
esac
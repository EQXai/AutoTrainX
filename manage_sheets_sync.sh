#!/bin/bash
# Manage Google Sheets Sync Daemon for AutoTrainX

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configure PostgreSQL environment
export AUTOTRAINX_DB_TYPE=postgresql
export AUTOTRAINX_DB_HOST=localhost
export AUTOTRAINX_DB_PORT=5432
export AUTOTRAINX_DB_NAME=autotrainx
export AUTOTRAINX_DB_USER=autotrainx
export AUTOTRAINX_DB_PASSWORD=1234

show_help() {
    echo -e "${BLUE}Google Sheets Sync Manager for AutoTrainX${NC}"
    echo
    echo "Usage: $0 [command]"
    echo
    echo "Commands:"
    echo "  start       Start daemon in foreground (see logs)"
    echo "  start -d    Start daemon in background"
    echo "  stop        Stop the daemon"
    echo "  restart     Restart the daemon"
    echo "  status      Show daemon status"
    echo "  logs        Show recent logs"
    echo "  follow      Follow logs in real-time"
    echo "  test        Run connection tests"
    echo "  help        Show this help"
    echo
}

case "$1" in
    start)
        if [ "$2" == "-d" ] || [ "$2" == "--daemon" ]; then
            echo -e "${GREEN}Starting Google Sheets Sync daemon (PostgreSQL) in background...${NC}"
            python sheets_sync_daemon.py --daemon
        else
            echo -e "${GREEN}Starting Google Sheets Sync daemon (PostgreSQL) in foreground...${NC}"
            echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
            python sheets_sync_daemon.py
        fi
        ;;
    
    stop)
        echo -e "${YELLOW}Stopping Google Sheets Sync daemon...${NC}"
        python sheets_sync_daemon.py --stop
        ;;
    
    restart)
        echo -e "${YELLOW}Restarting Google Sheets Sync daemon...${NC}"
        python sheets_sync_daemon.py --stop
        sleep 2
        python sheets_sync_daemon.py --daemon
        sleep 2
        python sheets_sync_daemon.py --status
        ;;
    
    status)
        echo -e "${BLUE}Database Configuration:${NC}"
        echo -e "  Type: ${GREEN}PostgreSQL${NC}"
        echo -e "  Host: $AUTOTRAINX_DB_HOST:$AUTOTRAINX_DB_PORT"
        echo -e "  Database: $AUTOTRAINX_DB_NAME"
        echo
        python sheets_sync_daemon.py --status
        ;;
    
    logs)
        if [ -f logs/sheets_sync_daemon.log ]; then
            echo -e "${BLUE}Recent logs:${NC}"
            tail -50 logs/sheets_sync_daemon.log
        else
            echo -e "${RED}Log file not found${NC}"
        fi
        ;;
    
    follow)
        if [ -f logs/sheets_sync_daemon.log ]; then
            echo -e "${BLUE}Following logs (Ctrl+C to stop):${NC}"
            tail -f logs/sheets_sync_daemon.log
        else
            echo -e "${RED}Log file not found${NC}"
        fi
        ;;
    
    test)
        echo -e "${BLUE}Running connection tests...${NC}"
        python test_sheets_sync_postgresql.py
        ;;
    
    help|"")
        show_help
        ;;
    
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo
        show_help
        exit 1
        ;;
esac
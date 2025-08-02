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
NC='\033[0m'

echo -e "${GREEN}Starting Google Sheets Sync with PostgreSQL...${NC}"
echo -e "${YELLOW}Database: PostgreSQL @ $AUTOTRAINX_DB_HOST:$AUTOTRAINX_DB_PORT/$AUTOTRAINX_DB_NAME${NC}"

# Start the daemon
if [ "$1" == "--daemon" ] || [ "$1" == "-d" ]; then
    echo "Starting in daemon mode..."
    python sheets_sync_daemon.py --daemon
else
    echo "Starting in foreground mode (Ctrl+C to stop)..."
    python sheets_sync_daemon.py
fi
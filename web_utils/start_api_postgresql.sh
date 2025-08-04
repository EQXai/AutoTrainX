#!/bin/bash
# Start API Server with PostgreSQL configuration

# Get the script directory and parent directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if API is already running
if pgrep -f "api_server.py" > /dev/null; then
    echo -e "${YELLOW}API server is already running. Stopping it first...${NC}"
    pkill -f "api_server.py"
    sleep 2
fi

# Change to parent directory
cd "$PARENT_DIR"

# Ensure settings/.env file exists
mkdir -p settings
if [ ! -f "settings/.env" ]; then
    echo -e "${RED}Error: settings/.env file not found!${NC}"
    echo -e "${YELLOW}Please create settings/.env file with the following configuration:${NC}"
    echo
    echo "# AutoTrainX Database Configuration"
    echo "DATABASE_TYPE=postgresql"
    echo "DATABASE_URL=postgresql://autotrainx:<password>@localhost:5432/autotrainx"
    echo "DATABASE_HOST=localhost"
    echo "DATABASE_PORT=5432"
    echo "DATABASE_NAME=autotrainx"
    echo "DATABASE_USER=autotrainx"
    echo "DATABASE_PASSWORD=<your-secure-password>"
    echo
    echo -e "${RED}Cannot continue without proper configuration.${NC}"
    exit 1
fi

# Load environment variables from .env file
if [ -f "settings/.env" ]; then
    set -a
    source settings/.env
    set +a
fi

# Verify required variables are set
if [ -z "$DATABASE_PASSWORD" ] && [ -z "$AUTOTRAINX_DB_PASSWORD" ]; then
    echo -e "${RED}Error: DATABASE_PASSWORD not set in settings/.env${NC}"
    exit 1
fi

echo -e "${GREEN}Starting API Server with PostgreSQL...${NC}"
echo -e "${YELLOW}Database: PostgreSQL @ localhost:5432/autotrainx${NC}"
echo -e "${YELLOW}API URL: http://localhost:8090${NC}"
echo

# Start the API server
python api_server.py
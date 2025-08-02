#!/bin/bash
# Start API Server with PostgreSQL configuration

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

# Ensure .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Creating .env file with PostgreSQL configuration..."
    
    cat > .env << 'EOF'
# AutoTrainX Database Configuration
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://autotrainx:1234@localhost:5432/autotrainx
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=autotrainx
DATABASE_USER=autotrainx
DATABASE_PASSWORD=1234
DATABASE_POOL_SIZE=10
DATABASE_ECHO=false

# Legacy support
AUTOTRAINX_DB_TYPE=postgresql
AUTOTRAINX_DB_HOST=localhost
AUTOTRAINX_DB_PORT=5432
AUTOTRAINX_DB_NAME=autotrainx
AUTOTRAINX_DB_USER=autotrainx
AUTOTRAINX_DB_PASSWORD=1234
EOF
    echo -e "${GREEN}Created .env file with PostgreSQL configuration${NC}"
fi

# Export environment variables
export DATABASE_TYPE=postgresql
export DATABASE_URL=postgresql://autotrainx:1234@localhost:5432/autotrainx
export AUTOTRAINX_DB_TYPE=postgresql
export AUTOTRAINX_DB_HOST=localhost
export AUTOTRAINX_DB_PORT=5432
export AUTOTRAINX_DB_NAME=autotrainx
export AUTOTRAINX_DB_USER=autotrainx
export AUTOTRAINX_DB_PASSWORD=1234

echo -e "${GREEN}Starting API Server with PostgreSQL...${NC}"
echo -e "${YELLOW}Database: PostgreSQL @ localhost:5432/autotrainx${NC}"
echo -e "${YELLOW}API URL: http://localhost:8090${NC}"
echo

# Start the API server
python api_server.py
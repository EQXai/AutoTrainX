#!/bin/bash
# AutoTrainX Unified Development Server
# Starts both backend API and frontend with automatic port cleanup

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3000
POSTGRES_PORT=5432

# Cleanup function
cleanup_ports() {
    echo -e "${YELLOW}Cleaning up ports...${NC}"
    
    # Kill processes on specific ports
    for port in $BACKEND_PORT $FRONTEND_PORT; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "${YELLOW}Killing process on port $port${NC}"
            kill $(lsof -Pi :$port -sTCP:LISTEN -t) 2>/dev/null || true
            sleep 1
        fi
    done
    
    # Kill specific processes
    pkill -f "api_server.py" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    pkill -f "node.*next.*dev" 2>/dev/null || true
    
    sleep 2
    echo -e "${GREEN}Port cleanup completed${NC}"
}

# Trap to cleanup on script exit
trap cleanup_ports EXIT INT TERM

# Cleanup ports at start
cleanup_ports

# Ensure .env file exists for backend
mkdir -p settings
if [ ! -f "settings/.env" ]; then
    echo -e "${RED}Error: settings/.env file not found!${NC}"
    echo -e "${YELLOW}Please create settings/.env file with database configuration.${NC}"
    echo -e "${YELLOW}See .env.example for reference.${NC}"
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

# Check if PostgreSQL is running
if ! nc -z localhost $POSTGRES_PORT 2>/dev/null; then
    echo -e "${RED}Warning: PostgreSQL is not running on port $POSTGRES_PORT${NC}"
    echo -e "${YELLOW}Please start PostgreSQL first${NC}"
fi

# Create log directories
mkdir -p logs/api_log
mkdir -p logs/frontend_log

echo -e "${BLUE}===========================================${NC}"
echo -e "${GREEN}   AutoTrainX Development Environment${NC}"
echo -e "${BLUE}===========================================${NC}"
echo -e "${YELLOW}Backend API: http://localhost:$BACKEND_PORT${NC}"
echo -e "${YELLOW}Frontend:    http://localhost:$FRONTEND_PORT${NC}"
echo -e "${YELLOW}Database:    PostgreSQL @ localhost:$POSTGRES_PORT${NC}"
echo -e "${BLUE}===========================================${NC}"
echo

# Start backend in background
echo -e "${GREEN}Starting Backend API Server...${NC}"
python api_server.py --host 0.0.0.0 --port $BACKEND_PORT --dev > logs/api_log/api_server.log 2>&1 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Check if backend started successfully
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Failed to start backend server${NC}"
    echo -e "${YELLOW}Check logs/api_log/api_server.log for details${NC}"
    exit 1
fi

echo -e "${GREEN}Backend server started (PID: $BACKEND_PID)${NC}"

# Start frontend in background
echo -e "${GREEN}Starting Frontend Development Server...${NC}"
cd autotrainx-web
npm run dev > ../logs/frontend_log/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait a moment for frontend to start
sleep 3

# Check if frontend started successfully
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}Failed to start frontend server${NC}"
    echo -e "${YELLOW}Check logs/frontend_log/frontend.log for details${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}Frontend server started (PID: $FRONTEND_PID)${NC}"
echo
echo -e "${GREEN}✅ Both servers are running!${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"
echo
echo -e "${BLUE}Logs:${NC}"
echo -e "  Backend:  logs/api_log/api_server.log"
echo -e "  Frontend: logs/frontend_log/frontend.log"
echo

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
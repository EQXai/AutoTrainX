#!/bin/bash
# AutoTrainX Development Server Stop Script
# Stops all development servers and cleans up ports

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3000

echo -e "${YELLOW}Stopping AutoTrainX Development Environment...${NC}"

# Function to stop processes by port
stop_port() {
    local port=$1
    local name=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}Stopping $name on port $port${NC}"
        kill $(lsof -Pi :$port -sTCP:LISTEN -t) 2>/dev/null || true
        sleep 1
        
        # Force kill if still running
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "${YELLOW}Force stopping $name on port $port${NC}"
            kill -9 $(lsof -Pi :$port -sTCP:LISTEN -t) 2>/dev/null || true
        fi
        echo -e "${GREEN}$name stopped${NC}"
    else
        echo -e "${YELLOW}$name is not running on port $port${NC}"
    fi
}

# Function to stop processes by name
stop_process() {
    local process_name=$1
    local display_name=$2
    
    if pgrep -f "$process_name" > /dev/null; then
        echo -e "${YELLOW}Stopping $display_name processes${NC}"
        pkill -f "$process_name" 2>/dev/null || true
        sleep 1
        
        # Force kill if still running
        if pgrep -f "$process_name" > /dev/null; then
            echo -e "${YELLOW}Force stopping $display_name processes${NC}"
            pkill -9 -f "$process_name" 2>/dev/null || true
        fi
        echo -e "${GREEN}$display_name processes stopped${NC}"
    else
        echo -e "${YELLOW}No $display_name processes running${NC}"
    fi
}

# Stop by port
stop_port $BACKEND_PORT "Backend API"
stop_port $FRONTEND_PORT "Frontend"

# Stop by process name (backup method)
stop_process "api_server.py" "Backend API"
stop_process "next dev" "Frontend"
stop_process "node.*next.*dev" "Frontend Node"

# Final cleanup
echo -e "${YELLOW}Final cleanup...${NC}"
sleep 2

# Check if anything is still running
if lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1 || lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}Some processes may still be running. Check manually with:${NC}"
    echo "  lsof -i :$BACKEND_PORT"
    echo "  lsof -i :$FRONTEND_PORT"
else
    echo -e "${GREEN}✅ All development servers stopped successfully${NC}"
fi

echo -e "${GREEN}Port cleanup completed${NC}"
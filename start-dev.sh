#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting AutoTrainX Development Environment...${NC}"

# Start API server in background
echo -e "${GREEN}Starting API server...${NC}"
python api_server.py --dev &
API_PID=$!

# Wait for API to start
sleep 3

# Start Next.js dev server
echo -e "${GREEN}Starting web interface...${NC}"
cd autotrainx-web
npm run dev &
WEB_PID=$!

echo -e "${BLUE}Development environment started!${NC}"
echo -e "API Server: http://localhost:8000"
echo -e "Web Interface: http://localhost:3000"
echo -e "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${BLUE}Stopping servers...${NC}"
    kill $API_PID 2>/dev/null
    kill $WEB_PID 2>/dev/null
    exit 0
}

# Set trap to cleanup on Ctrl+C
trap cleanup INT

# Wait for both processes
wait $API_PID $WEB_PID
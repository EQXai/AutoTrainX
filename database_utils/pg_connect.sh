#!/bin/bash
source ~/.bashrc 2>/dev/null || true

# Colors
BOLD='\033[1m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${BOLD}Connecting to AutoTrainX PostgreSQL...${NC}"
echo -e "${GREEN}Tip: Use \\? for help, \\dt to list tables, \\q to quit${NC}"
echo

psql -h ${AUTOTRAINX_DB_HOST:-localhost} \
     -p ${AUTOTRAINX_DB_PORT:-5432} \
     -U ${AUTOTRAINX_DB_USER:-autotrainx} \
     -d ${AUTOTRAINX_DB_NAME:-autotrainx}

#!/bin/bash
# Quick PostgreSQL Status Check for AutoTrainX

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   AutoTrainX PostgreSQL Status${NC}"
echo -e "${GREEN}================================================${NC}"
echo

# Check PostgreSQL service
echo -e "${YELLOW}PostgreSQL Service:${NC}"
if systemctl is-active --quiet postgresql; then
    echo -e "  Status: ${GREEN}● Running${NC}"
    VERSION=$(sudo -u postgres psql -t -c "SELECT version();" | head -n1 | cut -d' ' -f3)
    echo -e "  Version: PostgreSQL $VERSION"
else
    echo -e "  Status: ${RED}○ Not running${NC}"
    echo -e "  ${YELLOW}Start with: sudo systemctl start postgresql${NC}"
    exit 1
fi

echo

# Check database connection
echo -e "${YELLOW}Database Connection:${NC}"
if PGPASSWORD=1234 psql -h localhost -U autotrainx -d autotrainx -c '\q' 2>/dev/null; then
    echo -e "  Connection: ${GREEN}✓ Success${NC}"
else
    echo -e "  Connection: ${RED}✗ Failed${NC}"
    echo -e "  ${YELLOW}Run ./database_utils/setup_postgresql.sh to configure${NC}"
    exit 1
fi

echo

# Get database statistics
echo -e "${YELLOW}Database Statistics:${NC}"
STATS=$(PGPASSWORD=1234 psql -h localhost -U autotrainx -d autotrainx -t << EOF
SELECT 
    (SELECT COUNT(*) FROM executions) as total_executions,
    (SELECT COUNT(*) FROM executions WHERE success = true) as successful,
    (SELECT COUNT(*) FROM executions WHERE success = false) as failed,
    (SELECT COUNT(*) FROM executions WHERE status = 'training') as training,
    (SELECT pg_size_pretty(pg_database_size('autotrainx'))) as db_size;
EOF
)

IFS='|' read -r TOTAL SUCCESS FAILED TRAINING SIZE <<< "$STATS"

echo -e "  Total Executions: ${GREEN}$TOTAL${NC}"
echo -e "  Successful: ${GREEN}$SUCCESS${NC}"
echo -e "  Failed: ${RED}$FAILED${NC}"
echo -e "  Currently Training: ${YELLOW}$TRAINING${NC}"
echo -e "  Database Size: $SIZE"

echo

# Check environment variables
echo -e "${YELLOW}AutoTrainX Configuration:${NC}"
if [ "$AUTOTRAINX_DB_TYPE" = "postgresql" ]; then
    echo -e "  DB Type: ${GREEN}PostgreSQL${NC} ✓"
    echo -e "  DB Host: $AUTOTRAINX_DB_HOST"
    echo -e "  DB Name: $AUTOTRAINX_DB_NAME"
else
    echo -e "  DB Type: ${YELLOW}SQLite${NC} (PostgreSQL not configured)"
    echo -e "  ${YELLOW}Run: source ~/.bashrc${NC} to load PostgreSQL config"
fi

echo

# Show recent executions
echo -e "${YELLOW}Recent Executions:${NC}"
PGPASSWORD=1234 psql -h localhost -U autotrainx -d autotrainx -t << EOF | head -5
SELECT 
    '  ' || job_id || ' | ' || 
    RPAD(dataset_name, 15) || ' | ' || 
    RPAD(status, 12) || ' | ' || 
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI')
FROM executions 
ORDER BY created_at DESC 
LIMIT 5;
EOF

echo
echo -e "${GREEN}Quick Commands:${NC}"
echo "  Connect to DB:     psql -h localhost -U autotrainx -d autotrainx"
echo "  View in VSCode:    Use SQLTools extension"
echo "  Sync to SQLite:    python database_utils/sync_to_sqlite.py"
echo "  Full stats:        ./quick_stats.sh"
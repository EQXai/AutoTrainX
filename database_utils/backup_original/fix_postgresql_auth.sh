#!/bin/bash

# =====================================================
# Fix PostgreSQL Authentication in Docker
# =====================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Fixing PostgreSQL Authentication${NC}"
echo "=================================="
echo

# Find PostgreSQL version
PG_VER=$(ls /usr/lib/postgresql/ 2>/dev/null | grep -E '^[0-9]+' | head -1)
if [ -z "$PG_VER" ]; then
    echo -e "${RED}PostgreSQL not found${NC}"
    exit 1
fi

echo "PostgreSQL version: $PG_VER"

# Find pg_hba.conf
PG_HBA="/etc/postgresql/$PG_VER/main/pg_hba.conf"
PG_DATA="/var/lib/postgresql/$PG_VER/main"

if [ ! -f "$PG_HBA" ]; then
    # Try data directory
    PG_HBA="$PG_DATA/pg_hba.conf"
fi

if [ ! -f "$PG_HBA" ]; then
    echo -e "${RED}Cannot find pg_hba.conf${NC}"
    exit 1
fi

echo "Found pg_hba.conf at: $PG_HBA"
echo

# Step 1: Backup current configuration
cp "$PG_HBA" "$PG_HBA.backup.$(date +%Y%m%d_%H%M%S)"
echo "Backed up pg_hba.conf"

# Step 2: Temporarily allow trust authentication
echo "Setting temporary trust authentication..."
cat > "$PG_HBA" << 'EOF'
# Temporary trust authentication for setup
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
EOF

# Step 3: Reload PostgreSQL
echo "Reloading PostgreSQL configuration..."
if command -v service &> /dev/null; then
    service postgresql reload 2>/dev/null
else
    pkill -HUP postgres 2>/dev/null
fi
sleep 2

# Step 4: Create user and database
echo
echo "Creating database and user..."

# Connect without password
psql -U postgres << 'EOF'
-- Create user
CREATE USER autotrainx WITH PASSWORD '1234';

-- Create database
CREATE DATABASE autotrainx OWNER autotrainx;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE autotrainx TO autotrainx;

-- Show users and databases
\echo
\echo 'Users created:'
\du autotrainx
\echo
\echo 'Databases created:'
\l autotrainx
EOF

# Step 5: Set secure authentication
echo
echo "Setting secure authentication..."
cat > "$PG_HBA" << 'EOF'
# PostgreSQL Client Authentication Configuration
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Database administrative login by Unix domain socket
local   all             postgres                                peer

# "local" is for Unix domain socket connections only
local   all             all                                     md5

# IPv4 local connections:
host    all             all             127.0.0.1/32            md5

# IPv6 local connections:
host    all             all             ::1/128                 md5
EOF

# Step 6: Reload again
echo "Applying secure configuration..."
if command -v service &> /dev/null; then
    service postgresql reload 2>/dev/null
else
    pkill -HUP postgres 2>/dev/null
fi
sleep 2

# Step 7: Test connection
echo
echo "Testing connection..."
export PGPASSWORD='1234'

if psql -h localhost -U autotrainx -d autotrainx -c "SELECT 'Connection successful!' as status;" 2>/dev/null; then
    echo -e "${GREEN}✅ Success! Database is ready${NC}"
    
    # Save configuration
    cat > "./database_utils/.env" << EOF
# AutoTrainX PostgreSQL Configuration
AUTOTRAINX_DB_TYPE=postgresql
AUTOTRAINX_DB_HOST=localhost
AUTOTRAINX_DB_PORT=5432
AUTOTRAINX_DB_NAME=autotrainx
AUTOTRAINX_DB_USER=autotrainx
AUTOTRAINX_DB_PASSWORD=1234
EOF
    
    echo
    echo "Configuration saved to database_utils/.env"
    echo
    echo "To connect to the database:"
    echo "  PGPASSWORD=1234 psql -h localhost -U autotrainx -d autotrainx"
else
    echo -e "${RED}Connection test failed${NC}"
    echo
    echo "Try manually:"
    echo "1. psql -U postgres"
    echo "2. ALTER USER autotrainx WITH PASSWORD '1234';"
    echo "3. \\q"
fi

unset PGPASSWORD
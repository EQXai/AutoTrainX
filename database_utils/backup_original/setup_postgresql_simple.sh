#!/bin/bash

# =====================================================
# AutoTrainX PostgreSQL Setup - Simple Version
# =====================================================
# Direct approach for Docker containers
# =====================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Defaults
DB_NAME="${1:-autotrainx}"
DB_USER="${2:-autotrainx}"
DB_PASSWORD="${3:-1234}"

echo -e "${BLUE}AutoTrainX PostgreSQL Simple Setup${NC}"
echo "======================================"
echo

# Function to check if PostgreSQL is running
check_pg_running() {
    pg_isready -q 2>/dev/null || pgrep -f "postgres" > /dev/null 2>&1
}

# Function to start PostgreSQL
start_postgresql() {
    echo -e "${YELLOW}Starting PostgreSQL...${NC}"
    
    # Try service first
    if command -v service &> /dev/null; then
        service postgresql start 2>/dev/null
        sleep 2
    fi
    
    # Check if running
    if check_pg_running; then
        echo -e "${GREEN}PostgreSQL is running${NC}"
        return 0
    fi
    
    # Try direct start
    PG_VERSION=$(ls /usr/lib/postgresql/ 2>/dev/null | grep -E '^[0-9]+' | head -1)
    if [ -n "$PG_VERSION" ]; then
        su - postgres -c "/usr/lib/postgresql/$PG_VERSION/bin/postgres -D /var/lib/postgresql/$PG_VERSION/main" &
        sleep 3
    fi
    
    if check_pg_running; then
        echo -e "${GREEN}PostgreSQL started${NC}"
        return 0
    else
        echo -e "${RED}Failed to start PostgreSQL${NC}"
        return 1
    fi
}

# Start PostgreSQL if needed
if ! check_pg_running; then
    start_postgresql || exit 1
else
    echo -e "${GREEN}PostgreSQL is already running${NC}"
fi

echo
echo "Creating database and user..."
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo

# Create user - simple approach
su - postgres -c "psql" << EOF 2>/dev/null
-- Create user if not exists
DO
\$\$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_user
      WHERE usename = '$DB_USER') THEN
      CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
   END IF;
END
\$\$;

-- Update password
ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

-- Create database if not exists
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER' 
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
\\q
EOF

# Update pg_hba.conf for password authentication
echo
echo "Updating authentication configuration..."

PG_VERSION=$(ls /usr/lib/postgresql/ 2>/dev/null | grep -E '^[0-9]+' | head -1)
PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"

if [ -f "$PG_HBA" ]; then
    # Backup
    cp "$PG_HBA" "$PG_HBA.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Simple pg_hba.conf
    cat > "$PG_HBA" << 'EOF'
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             postgres                                peer
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
EOF
    
    # Reload
    su - postgres -c "psql -c 'SELECT pg_reload_conf();'" 2>/dev/null
    sleep 2
fi

# Test connection
echo
echo "Testing connection..."
export PGPASSWORD="$DB_PASSWORD"

if psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" 2>/dev/null | grep -q "PostgreSQL"; then
    echo -e "${GREEN}✅ Connection successful!${NC}"
else
    echo -e "${YELLOW}Connection test failed, trying to fix...${NC}"
    
    # Try with trust temporarily
    sed -i 's/md5/trust/g' "$PG_HBA"
    su - postgres -c "psql -c 'SELECT pg_reload_conf();'" 2>/dev/null
    sleep 1
    
    # Set password again
    su - postgres -c "psql -c \"ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';\"" 2>/dev/null
    
    # Restore md5
    sed -i 's/trust/md5/g' "$PG_HBA"
    sed -i '1s/md5/peer/' "$PG_HBA"  # First line back to peer
    su - postgres -c "psql -c 'SELECT pg_reload_conf();'" 2>/dev/null
    sleep 1
    
    # Test again
    if psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" 2>/dev/null; then
        echo -e "${GREEN}✅ Connection fixed!${NC}"
    else
        echo -e "${RED}❌ Connection still failing${NC}"
    fi
fi

# Save configuration
echo
echo "Saving configuration..."

cat > "./database_utils/.env" << EOF
# AutoTrainX PostgreSQL Configuration
AUTOTRAINX_DB_TYPE=postgresql
AUTOTRAINX_DB_HOST=localhost
AUTOTRAINX_DB_PORT=5432
AUTOTRAINX_DB_NAME=$DB_NAME
AUTOTRAINX_DB_USER=$DB_USER
AUTOTRAINX_DB_PASSWORD=$DB_PASSWORD
EOF

echo -e "${GREEN}Configuration saved to .env${NC}"

# Create simple helper scripts
cat > "./database_utils/pg_start.sh" << 'EOF'
#!/bin/bash
service postgresql start 2>/dev/null || \
su - postgres -c "/usr/lib/postgresql/*/bin/postgres -D /var/lib/postgresql/*/main" &
EOF
chmod +x ./database_utils/pg_start.sh

cat > "./database_utils/pg_connect.sh" << EOF
#!/bin/bash
PGPASSWORD=$DB_PASSWORD psql -h localhost -U $DB_USER -d $DB_NAME
EOF
chmod +x ./database_utils/pg_connect.sh

echo
echo -e "${GREEN}✅ Setup complete!${NC}"
echo
echo "Helper scripts created:"
echo "  - ./database_utils/pg_start.sh   - Start PostgreSQL"
echo "  - ./database_utils/pg_connect.sh  - Connect to database"
echo
echo "To connect manually:"
echo "  PGPASSWORD=$DB_PASSWORD psql -h localhost -U $DB_USER -d $DB_NAME"
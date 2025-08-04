#!/bin/bash

# =====================================================
# AutoTrainX PostgreSQL Direct Setup
# =====================================================
# No heredocs, only direct commands
# =====================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Defaults
DB_NAME="autotrainx"
DB_USER="autotrainx"
DB_PASSWORD="1234"

echo -e "${BLUE}AutoTrainX PostgreSQL Direct Setup${NC}"
echo "======================================"
echo

# Check if PostgreSQL is running
if pg_isready -q 2>/dev/null; then
    echo -e "${GREEN}PostgreSQL is running${NC}"
else
    echo -e "${YELLOW}Starting PostgreSQL...${NC}"
    service postgresql start 2>/dev/null || {
        # Find version and start manually
        PG_VER=$(ls /usr/lib/postgresql/ | grep -E '^[0-9]+' | head -1)
        su - postgres -c "/usr/lib/postgresql/$PG_VER/bin/postgres -D /var/lib/postgresql/$PG_VER/main" &
        sleep 3
    }
fi

echo
echo "Setting up database..."

# Method 1: Using createuser and createdb commands
echo "Creating user $DB_USER..."
su - postgres -c "psql -tAc \"SELECT 1 FROM pg_user WHERE usename='$DB_USER'\" | grep -q 1" || {
    echo "$DB_PASSWORD" | su - postgres -c "createuser -P -e $DB_USER" 2>/dev/null
}

echo "Creating database $DB_NAME..."
su - postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='$DB_NAME'\" | grep -q 1" || {
    su - postgres -c "createdb -O $DB_USER $DB_NAME" 2>/dev/null
}

# Method 2: Direct SQL commands
echo "Ensuring user and database exist..."
su - postgres -c "psql -c \"CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';\"" 2>/dev/null || true
su - postgres -c "psql -c \"ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';\"" 2>/dev/null
su - postgres -c "psql -c \"CREATE DATABASE $DB_NAME OWNER $DB_USER;\"" 2>/dev/null || true
su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;\"" 2>/dev/null

# Update pg_hba.conf
echo
echo "Configuring authentication..."

# Find pg_hba.conf
PG_VER=$(ls /usr/lib/postgresql/ | grep -E '^[0-9]+' | head -1)
PG_HBA="/etc/postgresql/$PG_VER/main/pg_hba.conf"

if [ -f "$PG_HBA" ]; then
    # Backup
    cp "$PG_HBA" "$PG_HBA.backup"
    
    # Update to allow md5 authentication
    grep -q "host.*all.*all.*127.0.0.1/32.*md5" "$PG_HBA" || {
        echo "host    all             all             127.0.0.1/32            md5" >> "$PG_HBA"
    }
    
    # Change local connections to md5 (except postgres user)
    sed -i 's/local   all             all                                     peer/local   all             all                                     md5/g' "$PG_HBA" 2>/dev/null || true
    
    # Reload configuration
    su - postgres -c "psql -c 'SELECT pg_reload_conf();'" 2>/dev/null || {
        service postgresql reload 2>/dev/null || pkill -HUP postgres
    }
    
    sleep 2
fi

# Test connection
echo
echo "Testing connection..."
export PGPASSWORD="$DB_PASSWORD"

if psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "SELECT 'Connection successful' as status;" 2>/dev/null; then
    echo -e "${GREEN}✅ Database setup complete!${NC}"
else
    echo -e "${YELLOW}Direct connection failed, trying alternative fix...${NC}"
    
    # Alternative: temporarily use trust auth
    cp "$PG_HBA" "$PG_HBA.md5"
    sed -i 's/md5/trust/g' "$PG_HBA"
    service postgresql reload 2>/dev/null || pkill -HUP postgres
    sleep 1
    
    # Reset password
    psql -h localhost -U postgres -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null
    
    # Restore md5 auth
    mv "$PG_HBA.md5" "$PG_HBA"
    service postgresql reload 2>/dev/null || pkill -HUP postgres
    sleep 1
    
    # Final test
    if psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" 2>/dev/null; then
        echo -e "${GREEN}✅ Connection fixed!${NC}"
    else
        echo -e "${RED}Connection still failing. Manual intervention may be needed.${NC}"
        echo "Try: su - postgres -c \"psql\""
        echo "Then: ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    fi
fi

# Save configuration
echo
echo "Saving configuration..."

mkdir -p settings 2>/dev/null
cat > "settings/.env" << EOF
AUTOTRAINX_DB_TYPE=postgresql
AUTOTRAINX_DB_HOST=localhost
AUTOTRAINX_DB_PORT=5432
AUTOTRAINX_DB_NAME=$DB_NAME
AUTOTRAINX_DB_USER=$DB_USER
AUTOTRAINX_DB_PASSWORD=$DB_PASSWORD
EOF

# Quick test script
cat > "database_utils/test_connection.sh" << EOF
#!/bin/bash
export PGPASSWORD=$DB_PASSWORD
echo "Testing PostgreSQL connection..."
psql -h localhost -U $DB_USER -d $DB_NAME -c "SELECT version();"
EOF
chmod +x database_utils/test_connection.sh

echo -e "${GREEN}Setup complete!${NC}"
echo
echo "Files created:"
echo "  - settings/.env"
echo "  - database_utils/test_connection.sh"
echo
echo "To connect:"
echo "  PGPASSWORD=$DB_PASSWORD psql -h localhost -U $DB_USER -d $DB_NAME"
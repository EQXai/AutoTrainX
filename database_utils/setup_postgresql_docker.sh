#!/bin/bash

# =====================================================
# AutoTrainX PostgreSQL Docker Setup Script V2
# =====================================================
# Enhanced version with better detection
# =====================================================

# Colors for better UI
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Default values
DEFAULT_DB_NAME="autotrainx"
DEFAULT_DB_USER="autotrainx"
DEFAULT_DB_PASSWORD="1234"
DEFAULT_DB_HOST="localhost"
DEFAULT_DB_PORT="5432"

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Detect if running in Docker
IS_DOCKER=false
if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    IS_DOCKER=true
fi

# =====================================================
# Helper Functions
# =====================================================

print_header() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║   AutoTrainX PostgreSQL Setup (Docker Optimized V2)          ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -e "${YELLOW}Environment: ${IS_DOCKER:+Docker Container}${IS_DOCKER:-Host System}${NC}"
    echo -e "${YELLOW}User: $(whoami)${NC}"
    echo
}

print_section() {
    echo -e "\n${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}${BOLD}  $1${NC}"
    echo -e "${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_step() {
    echo -e "${CYAN}▶️  $1${NC}"
}

# Enhanced PostgreSQL detection
check_postgresql_installed() {
    # Check for psql command
    if ! command -v psql &> /dev/null; then
        return 1
    fi
    
    # Check for PostgreSQL binaries in common locations
    local pg_versions=(14 13 12 11 10 9.6 9.5)
    for version in "${pg_versions[@]}"; do
        if [ -f "/usr/lib/postgresql/$version/bin/postgres" ]; then
            export PG_VERSION=$version
            export PG_BIN="/usr/lib/postgresql/$version/bin"
            return 0
        fi
    done
    
    # Check if postgresql package is installed
    if dpkg -l | grep -q "^ii.*postgresql-[0-9]"; then
        # Extract version from package
        PG_VERSION=$(dpkg -l | grep "^ii.*postgresql-[0-9]" | awk '{print $2}' | grep -oE '[0-9]+' | head -1)
        export PG_BIN="/usr/lib/postgresql/$PG_VERSION/bin"
        return 0
    fi
    
    return 1
}

# Function to find PostgreSQL data directory
find_pg_data_dir() {
    local pg_version=${PG_VERSION:-$(ls /usr/lib/postgresql/ 2>/dev/null | grep -E '^[0-9]+' | sort -V | tail -1)}
    echo "/var/lib/postgresql/${pg_version}/main"
}

# Function to check if PostgreSQL is running
check_postgresql_running() {
    # Method 1: Check with pg_isready
    if command -v pg_isready &> /dev/null && pg_isready -q 2>/dev/null; then
        return 0
    fi
    
    # Method 2: Check for postgres process
    if pgrep -f "postgres.*-D" > /dev/null 2>&1; then
        return 0
    fi
    
    # Method 3: Try to connect
    if su - postgres -c "psql -c 'SELECT 1;'" &>/dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

# Function to initialize PostgreSQL cluster
init_postgresql_cluster() {
    local pg_data=$(find_pg_data_dir)
    
    print_step "Checking PostgreSQL cluster..."
    
    if [ -f "$pg_data/PG_VERSION" ]; then
        print_info "PostgreSQL cluster already initialized"
        return 0
    fi
    
    print_step "Initializing new PostgreSQL cluster..."
    
    # Create data directory
    mkdir -p "$pg_data"
    chown -R postgres:postgres /var/lib/postgresql
    chmod 700 "$pg_data"
    
    # Initialize cluster
    su - postgres -c "$PG_BIN/initdb -D $pg_data --encoding=UTF8 --locale=en_US.UTF-8"
    
    if [ $? -eq 0 ]; then
        print_success "PostgreSQL cluster initialized"
        
        # Copy default configuration files if they don't exist
        local pg_config_dir="/etc/postgresql/$PG_VERSION/main"
        if [ ! -d "$pg_config_dir" ]; then
            mkdir -p "$pg_config_dir"
            cp "$pg_data"/*.conf "$pg_config_dir/" 2>/dev/null || true
        fi
        
        return 0
    else
        print_error "Failed to initialize PostgreSQL cluster"
        return 1
    fi
}

# Function to start PostgreSQL
start_postgresql() {
    print_step "Starting PostgreSQL..."
    
    if check_postgresql_running; then
        print_info "PostgreSQL is already running"
        return 0
    fi
    
    # Initialize cluster if needed
    init_postgresql_cluster
    
    local pg_data=$(find_pg_data_dir)
    local pg_config="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
    
    # Use config from data dir if etc config doesn't exist
    if [ ! -f "$pg_config" ]; then
        pg_config="$pg_data/postgresql.conf"
    fi
    
    # Start PostgreSQL
    print_step "Starting PostgreSQL service..."
    
    # Try using service command first
    if command -v service &> /dev/null; then
        service postgresql start 2>/dev/null
        if check_postgresql_running; then
            print_success "PostgreSQL started with service command"
            return 0
        fi
    fi
    
    # Fallback to manual start
    su - postgres -c "$PG_BIN/postgres -D $pg_data -c config_file=$pg_config" >> /var/log/postgresql/postgresql.log 2>&1 &
    
    # Wait for PostgreSQL to start
    local count=0
    while [ $count -lt 30 ]; do
        if check_postgresql_running; then
            print_success "PostgreSQL started successfully"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        echo -n "."
    done
    echo
    
    print_error "Failed to start PostgreSQL"
    return 1
}

# =====================================================
# Installation Functions
# =====================================================

install_or_verify_postgresql() {
    print_section "PostgreSQL Installation Check"
    
    # First check if PostgreSQL is already installed
    if check_postgresql_installed; then
        print_success "PostgreSQL is installed"
        print_info "Version: PostgreSQL $PG_VERSION"
        print_info "Binary path: $PG_BIN"
        
        # Verify psql works
        if command -v psql &> /dev/null; then
            local psql_version=$(psql --version 2>/dev/null | awk '{print $3}')
            print_info "psql version: $psql_version"
        fi
        
        return 0
    fi
    
    # PostgreSQL not detected, try to install
    print_warning "PostgreSQL not detected"
    echo
    read -p "Do you want to install PostgreSQL? [Y/n]: " response
    response=${response:-Y}
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_error "PostgreSQL is required to continue"
        return 1
    fi
    
    print_step "Installing PostgreSQL..."
    apt-get update
    apt-get install -y postgresql postgresql-contrib postgresql-client
    
    # Re-check after installation
    if check_postgresql_installed; then
        print_success "PostgreSQL installed successfully"
        return 0
    else
        print_error "Failed to install PostgreSQL"
        return 1
    fi
}

# =====================================================
# Configuration Functions
# =====================================================

configure_postgresql() {
    print_section "PostgreSQL Configuration"
    
    # Ensure PostgreSQL is running
    if ! check_postgresql_running; then
        if ! start_postgresql; then
            print_error "Cannot start PostgreSQL"
            return 1
        fi
    fi
    
    # Get configuration
    echo -e "${BOLD}Database Configuration:${NC}"
    echo
    
    read -p "Database name [$DEFAULT_DB_NAME]: " db_name
    db_name=${db_name:-$DEFAULT_DB_NAME}
    
    read -p "Database user [$DEFAULT_DB_USER]: " db_user
    db_user=${db_user:-$DEFAULT_DB_USER}
    
    read -sp "Database password [$DEFAULT_DB_PASSWORD]: " db_password
    db_password=${db_password:-$DEFAULT_DB_PASSWORD}
    echo
    
    # Create user and database
    print_step "Creating database and user..."
    
    su - postgres << EOF
psql << SQL
-- Create user
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '$db_user') THEN
        CREATE USER $db_user WITH PASSWORD '$db_password';
    ELSE
        ALTER USER $db_user WITH PASSWORD '$db_password';
    END IF;
END
\$\$;

-- Create database
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db_name') THEN
        CREATE DATABASE $db_name OWNER $db_user;
    END IF;
END
\$\$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $db_name TO $db_user;
SQL
EOF
    
    if [ $? -eq 0 ]; then
        print_success "Database configured successfully"
    else
        print_error "Failed to configure database"
        return 1
    fi
    
    # Update authentication
    update_pg_auth
    
    # Test connection
    print_step "Testing connection..."
    export PGPASSWORD="$db_password"
    if psql -h localhost -p 5432 -U "$db_user" -d "$db_name" -c "SELECT 1;" &>/dev/null; then
        print_success "Connection test passed"
    else
        print_warning "Connection test failed - checking authentication..."
        fix_authentication
    fi
    
    # Save configuration
    save_config "$db_name" "$db_user" "$db_password"
}

update_pg_auth() {
    local pg_hba="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
    
    # Find pg_hba.conf
    if [ ! -f "$pg_hba" ]; then
        pg_hba=$(find /etc/postgresql -name pg_hba.conf 2>/dev/null | head -1)
    fi
    
    if [ ! -f "$pg_hba" ]; then
        local pg_data=$(find_pg_data_dir)
        pg_hba="$pg_data/pg_hba.conf"
    fi
    
    if [ -f "$pg_hba" ]; then
        print_step "Updating authentication in $pg_hba"
        
        # Backup
        cp "$pg_hba" "$pg_hba.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Update authentication
        sed -i 's/local   all             all                                     peer/local   all             all                                     md5/g' "$pg_hba"
        sed -i 's/local   all             all                                     ident/local   all             all                                     md5/g' "$pg_hba"
        
        # Add host entries if not present
        if ! grep -q "host.*all.*all.*127.0.0.1/32.*md5" "$pg_hba"; then
            echo "host    all             all             127.0.0.1/32            md5" >> "$pg_hba"
        fi
        
        if ! grep -q "host.*all.*all.*::1/128.*md5" "$pg_hba"; then
            echo "host    all             all             ::1/128                 md5" >> "$pg_hba"
        fi
        
        # Reload configuration
        su - postgres -c "$PG_BIN/pg_ctl reload -D $(find_pg_data_dir)" 2>/dev/null || \
        pkill -HUP postgres 2>/dev/null || true
        
        sleep 2
    fi
}

fix_authentication() {
    print_step "Attempting to fix authentication..."
    
    # Temporarily allow trust authentication
    local pg_hba="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
    if [ ! -f "$pg_hba" ]; then
        pg_hba="$(find_pg_data_dir)/pg_hba.conf"
    fi
    
    if [ -f "$pg_hba" ]; then
        cp "$pg_hba" "$pg_hba.temp"
        
        # Temporarily set to trust
        sed -i 's/local   all             all                                     md5/local   all             all                                     trust/g' "$pg_hba"
        sed -i 's/host    all             all             127.0.0.1\/32            md5/host    all             all             127.0.0.1\/32            trust/g' "$pg_hba"
        
        # Reload
        pkill -HUP postgres 2>/dev/null || true
        sleep 2
        
        # Reset password
        psql -U postgres -c "ALTER USER $db_user WITH PASSWORD '$db_password';" 2>/dev/null
        
        # Restore md5 auth
        mv "$pg_hba.temp" "$pg_hba"
        pkill -HUP postgres 2>/dev/null || true
        sleep 2
    fi
}

save_config() {
    local db_name=$1
    local db_user=$2
    local db_password=$3
    
    print_step "Saving configuration..."
    
    cat > "$SCRIPT_DIR/.env" << EOF
# AutoTrainX PostgreSQL Configuration
AUTOTRAINX_DB_TYPE=postgresql
AUTOTRAINX_DB_HOST=localhost
AUTOTRAINX_DB_PORT=5432
AUTOTRAINX_DB_NAME=$db_name
AUTOTRAINX_DB_USER=$db_user
AUTOTRAINX_DB_PASSWORD=$db_password
EOF
    
    chmod 600 "$SCRIPT_DIR/.env"
    print_success "Configuration saved to .env"
}

# =====================================================
# Create helper scripts
# =====================================================

create_helper_scripts() {
    print_step "Creating helper scripts..."
    
    # PostgreSQL start script
    cat > "$SCRIPT_DIR/start_postgresql_docker.sh" << EOF
#!/bin/bash
# Start PostgreSQL in Docker

PG_VERSION=$PG_VERSION
PG_BIN=$PG_BIN
PG_DATA=$(find_pg_data_dir)

if pgrep -f "postgres.*-D" > /dev/null; then
    echo "PostgreSQL is already running"
    exit 0
fi

echo "Starting PostgreSQL..."
su - postgres -c "\$PG_BIN/postgres -D \$PG_DATA" >> /var/log/postgresql/postgresql.log 2>&1 &

# Wait for startup
count=0
while [ \$count -lt 30 ]; do
    if pg_isready -q 2>/dev/null; then
        echo "PostgreSQL started successfully"
        exit 0
    fi
    sleep 1
    count=\$((count + 1))
done

echo "Failed to start PostgreSQL"
exit 1
EOF
    
    chmod +x "$SCRIPT_DIR/start_postgresql_docker.sh"
    
    # Connection script
    cat > "$SCRIPT_DIR/connect_db.sh" << EOF
#!/bin/bash
# Connect to AutoTrainX database

source $SCRIPT_DIR/.env 2>/dev/null

psql -h \${AUTOTRAINX_DB_HOST:-localhost} \\
     -p \${AUTOTRAINX_DB_PORT:-5432} \\
     -U \${AUTOTRAINX_DB_USER:-autotrainx} \\
     -d \${AUTOTRAINX_DB_NAME:-autotrainx}
EOF
    
    chmod +x "$SCRIPT_DIR/connect_db.sh"
    
    print_success "Helper scripts created"
}

# =====================================================
# Main function
# =====================================================

main() {
    print_header
    
    if [ "$IS_DOCKER" = true ]; then
        print_info "Running in Docker container"
    fi
    
    echo
    read -p "Continue with setup? [Y/n]: " response
    response=${response:-Y}
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_warning "Setup cancelled"
        exit 0
    fi
    
    # Step 1: Install/Verify PostgreSQL
    if ! install_or_verify_postgresql; then
        print_error "Setup failed"
        exit 1
    fi
    
    # Step 2: Configure
    if ! configure_postgresql; then
        print_error "Configuration failed"
        exit 1
    fi
    
    # Step 3: Create helper scripts
    create_helper_scripts
    
    # Complete
    print_section "Setup Complete!"
    
    print_success "PostgreSQL configured for AutoTrainX"
    echo
    print_info "Next steps:"
    echo "1. Start PostgreSQL: ./database_utils/start_postgresql_docker.sh"
    echo "2. Connect to DB: ./database_utils/connect_db.sh"
    echo "3. Configuration: ./database_utils/.env"
    echo
    
    if [ "$IS_DOCKER" = true ]; then
        print_warning "Remember: In Docker, PostgreSQL must be started manually!"
    fi
}

# Run main
main
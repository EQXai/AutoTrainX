#!/bin/bash

# =====================================================
# AutoTrainX PostgreSQL Docker Setup Script V3
# =====================================================
# Enhanced with multiple methods and detailed logging
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
LOG_FILE="$SCRIPT_DIR/postgresql_setup.log"

# Initialize log
echo "PostgreSQL Setup Log - $(date)" > "$LOG_FILE"

# Global variables
IS_DOCKER=false
PG_VERSION=""
PG_BIN=""
INIT_SYSTEM="unknown"

# =====================================================
# Detection Functions
# =====================================================

detect_environment() {
    echo "=== Environment Detection ===" >> "$LOG_FILE"
    
    # Detect Docker
    if [ -f /.dockerenv ]; then
        IS_DOCKER=true
        echo "Docker detected: /.dockerenv exists" >> "$LOG_FILE"
    elif grep -q docker /proc/1/cgroup 2>/dev/null; then
        IS_DOCKER=true
        echo "Docker detected: /proc/1/cgroup contains 'docker'" >> "$LOG_FILE"
    elif [ -n "$DOCKER_CONTAINER" ]; then
        IS_DOCKER=true
        echo "Docker detected: DOCKER_CONTAINER env var set" >> "$LOG_FILE"
    fi
    
    # Detect init system
    if [ -d /run/systemd/system ]; then
        INIT_SYSTEM="systemd"
    elif command -v service &> /dev/null; then
        INIT_SYSTEM="sysvinit"
    elif [ -f /var/run/supervisord.pid ]; then
        INIT_SYSTEM="supervisord"
    fi
    
    echo "Environment: Docker=$IS_DOCKER, Init=$INIT_SYSTEM" >> "$LOG_FILE"
    echo "User: $(whoami), UID: $(id -u)" >> "$LOG_FILE"
}

# =====================================================
# Helper Functions
# =====================================================

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

print_header() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║   AutoTrainX PostgreSQL Setup (Docker Enhanced V3)           ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -e "${YELLOW}Environment: ${IS_DOCKER:+Docker Container}${IS_DOCKER:-Host System}${NC}"
    echo -e "${YELLOW}Init System: $INIT_SYSTEM${NC}"
    echo -e "${YELLOW}User: $(whoami)${NC}"
    echo -e "${YELLOW}Log File: $LOG_FILE${NC}"
    echo
}

print_section() {
    echo -e "\n${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}${BOLD}  $1${NC}"
    echo -e "${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    log_message "Section: $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    log_message "SUCCESS: $1"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    log_message "ERROR: $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    log_message "WARNING: $1"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
    log_message "INFO: $1"
}

print_step() {
    echo -e "${CYAN}▶️  $1${NC}"
    log_message "STEP: $1"
}

print_debug() {
    echo -e "${WHITE}🔍 DEBUG: $1${NC}"
    log_message "DEBUG: $1"
}

# =====================================================
# PostgreSQL Detection Functions
# =====================================================

detect_postgresql_version() {
    log_message "=== PostgreSQL Version Detection ==="
    
    # Method 1: Check installed packages
    if command -v dpkg &> /dev/null; then
        local pkg_versions=$(dpkg -l | grep "^ii.*postgresql-[0-9]" | awk '{print $2}' | grep -oE '[0-9]+(\.[0-9]+)?' | sort -V)
        if [ -n "$pkg_versions" ]; then
            PG_VERSION=$(echo "$pkg_versions" | tail -1)
            log_message "Detected from dpkg: PostgreSQL $PG_VERSION"
            return 0
        fi
    fi
    
    # Method 2: Check directories
    local found_versions=$(ls -d /usr/lib/postgresql/[0-9]* 2>/dev/null | grep -oE '[0-9]+(\.[0-9]+)?' | sort -V)
    if [ -n "$found_versions" ]; then
        PG_VERSION=$(echo "$found_versions" | tail -1)
        log_message "Detected from directories: PostgreSQL $PG_VERSION"
        return 0
    fi
    
    # Method 3: Check psql version
    if command -v psql &> /dev/null; then
        PG_VERSION=$(psql --version 2>/dev/null | grep -oE '[0-9]+(\.[0-9]+)?' | head -1 | cut -d. -f1)
        if [ -n "$PG_VERSION" ]; then
            log_message "Detected from psql: PostgreSQL $PG_VERSION"
            return 0
        fi
    fi
    
    log_message "Could not detect PostgreSQL version"
    return 1
}

find_postgresql_binaries() {
    log_message "=== Finding PostgreSQL Binaries ==="
    
    # Standard locations
    local possible_bins=(
        "/usr/lib/postgresql/$PG_VERSION/bin"
        "/usr/pgsql-$PG_VERSION/bin"
        "/opt/postgresql/$PG_VERSION/bin"
        "/usr/local/pgsql/bin"
    )
    
    for bin_path in "${possible_bins[@]}"; do
        if [ -f "$bin_path/postgres" ]; then
            PG_BIN="$bin_path"
            log_message "Found PostgreSQL binaries at: $PG_BIN"
            return 0
        fi
    done
    
    # Try to find with which
    local postgres_path=$(which postgres 2>/dev/null)
    if [ -n "$postgres_path" ]; then
        PG_BIN=$(dirname "$postgres_path")
        log_message "Found PostgreSQL binaries via which: $PG_BIN"
        return 0
    fi
    
    log_message "Could not find PostgreSQL binaries"
    return 1
}

check_postgresql_installed() {
    print_debug "Checking PostgreSQL installation..."
    
    # Check psql command
    if ! command -v psql &> /dev/null; then
        log_message "psql command not found in PATH"
        print_debug "psql not found in PATH"
        
        # Try to find psql in common locations
        local psql_locations=(
            "/usr/bin/psql"
            "/usr/local/bin/psql"
            "/usr/lib/postgresql/*/bin/psql"
        )
        
        for loc in "${psql_locations[@]}"; do
            if [ -f "$loc" ] || ls $loc 2>/dev/null | head -1 > /dev/null; then
                local found_psql=$(ls $loc 2>/dev/null | head -1)
                if [ -n "$found_psql" ]; then
                    print_debug "Found psql at: $found_psql"
                    export PATH="$(dirname $found_psql):$PATH"
                    break
                fi
            fi
        done
    fi
    
    # Detect version and binaries
    if detect_postgresql_version && find_postgresql_binaries; then
        print_debug "PostgreSQL $PG_VERSION detected with binaries at $PG_BIN"
        return 0
    fi
    
    # Final check: look for any postgresql package
    if command -v dpkg &> /dev/null && dpkg -l | grep -q "postgresql"; then
        print_debug "PostgreSQL packages found via dpkg"
        # Try to detect version again
        detect_postgresql_version
        find_postgresql_binaries
        return 0
    fi
    
    return 1
}

# =====================================================
# PostgreSQL Running Check Functions
# =====================================================

check_postgresql_running() {
    print_debug "Checking if PostgreSQL is running..."
    
    # Method 1: pg_isready
    if command -v pg_isready &> /dev/null; then
        if pg_isready -q 2>/dev/null; then
            log_message "PostgreSQL is running (pg_isready)"
            return 0
        else
            local pg_ready_output=$(pg_isready 2>&1)
            log_message "pg_isready output: $pg_ready_output"
        fi
    fi
    
    # Method 2: Check process
    if pgrep -f "postgres.*-D|postmaster.*-D" > /dev/null 2>&1; then
        log_message "PostgreSQL process found"
        return 0
    fi
    
    # Method 3: Check port
    if command -v ss &> /dev/null; then
        if ss -tlnp 2>/dev/null | grep -q ":5432"; then
            log_message "PostgreSQL port 5432 is listening"
            return 0
        fi
    elif command -v netstat &> /dev/null; then
        if netstat -tlnp 2>/dev/null | grep -q ":5432"; then
            log_message "PostgreSQL port 5432 is listening"
            return 0
        fi
    fi
    
    # Method 4: Try direct connection
    if su - postgres -c "psql -c 'SELECT 1;' postgres" &>/dev/null 2>&1; then
        log_message "PostgreSQL is running (direct connection)"
        return 0
    fi
    
    log_message "PostgreSQL is not running"
    return 1
}

# =====================================================
# PostgreSQL Start Functions
# =====================================================

find_pg_data_dir() {
    local pg_version=${PG_VERSION:-14}
    local possible_dirs=(
        "/var/lib/postgresql/$pg_version/main"
        "/var/lib/pgsql/$pg_version/data"
        "/usr/local/pgsql/data"
        "/opt/postgresql/$pg_version/data"
    )
    
    for dir in "${possible_dirs[@]}"; do
        if [ -f "$dir/PG_VERSION" ]; then
            echo "$dir"
            return 0
        fi
    done
    
    # Default
    echo "/var/lib/postgresql/$pg_version/main"
}

init_postgresql_cluster() {
    local pg_data=$(find_pg_data_dir)
    
    print_step "Checking PostgreSQL cluster at $pg_data..."
    
    if [ -f "$pg_data/PG_VERSION" ]; then
        print_info "PostgreSQL cluster already initialized"
        return 0
    fi
    
    print_step "Initializing new PostgreSQL cluster..."
    
    # Create directories
    mkdir -p "$pg_data"
    mkdir -p "/var/run/postgresql"
    chown -R postgres:postgres /var/lib/postgresql /var/run/postgresql
    chmod 700 "$pg_data"
    
    # Initialize
    local init_cmd="$PG_BIN/initdb -D $pg_data --encoding=UTF8"
    
    print_debug "Running: su - postgres -c \"$init_cmd\""
    if su - postgres -c "$init_cmd" >> "$LOG_FILE" 2>&1; then
        print_success "PostgreSQL cluster initialized"
        return 0
    else
        print_error "Failed to initialize cluster (check $LOG_FILE)"
        return 1
    fi
}

start_postgresql() {
    print_step "Starting PostgreSQL..."
    
    if check_postgresql_running; then
        print_info "PostgreSQL is already running"
        return 0
    fi
    
    # Initialize cluster if needed
    init_postgresql_cluster || return 1
    
    local pg_data=$(find_pg_data_dir)
    
    # Method 1: Using service (sysvinit)
    if [ "$INIT_SYSTEM" = "sysvinit" ] && command -v service &> /dev/null; then
        print_debug "Trying to start with service command..."
        if service postgresql start >> "$LOG_FILE" 2>&1; then
            sleep 3
            if check_postgresql_running; then
                print_success "Started with service command"
                return 0
            fi
        fi
    fi
    
    # Method 2: Using systemctl
    if [ "$INIT_SYSTEM" = "systemd" ] && command -v systemctl &> /dev/null; then
        print_debug "Trying to start with systemctl..."
        if systemctl start postgresql >> "$LOG_FILE" 2>&1; then
            sleep 3
            if check_postgresql_running; then
                print_success "Started with systemctl"
                return 0
            fi
        fi
    fi
    
    # Method 3: Direct start
    print_debug "Trying direct start..."
    local pg_conf="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
    if [ ! -f "$pg_conf" ]; then
        pg_conf="$pg_data/postgresql.conf"
    fi
    
    # Create log directory
    mkdir -p /var/log/postgresql
    chown postgres:postgres /var/log/postgresql
    
    # Start PostgreSQL
    local start_cmd="$PG_BIN/postgres -D $pg_data"
    if [ -f "$pg_conf" ]; then
        start_cmd="$start_cmd -c config_file=$pg_conf"
    fi
    
    print_debug "Starting with: $start_cmd"
    su - postgres -c "$start_cmd" >> /var/log/postgresql/postgresql.log 2>&1 &
    
    # Wait for startup
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
    print_info "Check logs: /var/log/postgresql/postgresql.log"
    tail -20 /var/log/postgresql/postgresql.log >> "$LOG_FILE"
    return 1
}

# =====================================================
# Database Configuration Functions
# =====================================================

create_database_and_user() {
    local db_name=$1
    local db_user=$2
    local db_password=$3
    
    print_step "Creating database and user..."
    
    # Method 1: Using psql with proper escaping
    local sql_file="$SCRIPT_DIR/create_db.sql"
    cat > "$sql_file" << EOF
-- Check and create user
DO
\$do\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$db_user') THEN
      CREATE USER $db_user WITH PASSWORD '$db_password';
   ELSE
      ALTER USER $db_user WITH PASSWORD '$db_password';
   END IF;
END
\$do\$;

-- Check and create database
SELECT 'CREATE DATABASE $db_name OWNER $db_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db_name')\\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $db_name TO $db_user;
EOF
    
    print_debug "Executing SQL from file..."
    if su - postgres -c "psql -f $sql_file" >> "$LOG_FILE" 2>&1; then
        rm -f "$sql_file"
        print_success "Database and user created successfully"
        return 0
    fi
    
    # Method 2: Individual commands
    print_warning "Trying alternative method..."
    
    # Create user
    if ! su - postgres -c "psql -tAc \"SELECT 1 FROM pg_user WHERE usename='$db_user'\"" | grep -q 1; then
        print_debug "Creating user $db_user..."
        su - postgres -c "createuser -P -e $db_user" << EOF
$db_password
$db_password
EOF
    else
        print_debug "User $db_user exists, updating password..."
        su - postgres -c "psql -c \"ALTER USER $db_user WITH PASSWORD '$db_password';\""
    fi
    
    # Create database
    if ! su - postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='$db_name'\"" | grep -q 1; then
        print_debug "Creating database $db_name..."
        su - postgres -c "createdb -O $db_user $db_name"
    else
        print_debug "Database $db_name already exists"
    fi
    
    # Grant privileges
    su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE $db_name TO $db_user;\""
    
    return 0
}

update_pg_auth() {
    print_step "Updating PostgreSQL authentication..."
    
    # Find pg_hba.conf
    local pg_hba_locations=(
        "/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
        "$(find_pg_data_dir)/pg_hba.conf"
        "/var/lib/pgsql/$PG_VERSION/data/pg_hba.conf"
    )
    
    local pg_hba=""
    for loc in "${pg_hba_locations[@]}"; do
        if [ -f "$loc" ]; then
            pg_hba="$loc"
            break
        fi
    done
    
    if [ -z "$pg_hba" ] || [ ! -f "$pg_hba" ]; then
        print_warning "Could not find pg_hba.conf"
        return 1
    fi
    
    print_debug "Found pg_hba.conf at: $pg_hba"
    
    # Backup
    cp "$pg_hba" "$pg_hba.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Update authentication methods
    print_debug "Updating authentication methods..."
    
    # Create new pg_hba.conf with proper settings
    cat > "$pg_hba.new" << 'EOF'
# PostgreSQL Client Authentication Configuration File
# ===================================================

# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     md5

# IPv4 local connections:
host    all             all             127.0.0.1/32            md5
host    all             all             localhost               md5

# IPv6 local connections:
host    all             all             ::1/128                 md5

# Allow replication connections from localhost, by a user with the
# replication privilege.
local   replication     all                                     peer
host    replication     all             127.0.0.1/32            md5
host    replication     all             ::1/128                 md5
EOF
    
    # Append any custom entries from original file
    if grep -v "^#\|^$\|^local\|^host" "$pg_hba" >> "$pg_hba.new" 2>/dev/null; then
        print_debug "Preserved custom entries from original pg_hba.conf"
    fi
    
    # Replace original
    mv "$pg_hba.new" "$pg_hba"
    chown postgres:postgres "$pg_hba"
    chmod 640 "$pg_hba"
    
    # Reload configuration
    print_debug "Reloading PostgreSQL configuration..."
    if [ -n "$PG_BIN" ] && [ -d "$PG_BIN" ]; then
        su - postgres -c "$PG_BIN/pg_ctl reload -D $(find_pg_data_dir)" 2>/dev/null || true
    fi
    pkill -HUP postgres 2>/dev/null || true
    
    sleep 2
    print_success "Authentication configuration updated"
    return 0
}

test_connection() {
    local db_name=$1
    local db_user=$2
    local db_password=$3
    local db_host=${4:-localhost}
    local db_port=${5:-5432}
    
    print_step "Testing database connection..."
    
    export PGPASSWORD="$db_password"
    
    # Test connection
    if psql -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" -c "SELECT version();" >> "$LOG_FILE" 2>&1; then
        print_success "Connection test successful!"
        unset PGPASSWORD
        return 0
    else
        print_error "Connection test failed"
        log_message "Connection test failed for $db_user@$db_host:$db_port/$db_name"
        unset PGPASSWORD
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
    echo -e "${BOLD}Enter database configuration:${NC}"
    echo
    
    read -p "Database name [$DEFAULT_DB_NAME]: " db_name
    db_name=${db_name:-$DEFAULT_DB_NAME}
    
    read -p "Database user [$DEFAULT_DB_USER]: " db_user
    db_user=${db_user:-$DEFAULT_DB_USER}
    
    read -sp "Database password [$DEFAULT_DB_PASSWORD]: " db_password
    db_password=${db_password:-$DEFAULT_DB_PASSWORD}
    echo
    
    read -p "Database host [$DEFAULT_DB_HOST]: " db_host
    db_host=${db_host:-$DEFAULT_DB_HOST}
    
    read -p "Database port [$DEFAULT_DB_PORT]: " db_port
    db_port=${db_port:-$DEFAULT_DB_PORT}
    
    echo
    print_info "Configuration summary:"
    echo "  Database: $db_name"
    echo "  User: $db_user"
    echo "  Host: $db_host"
    echo "  Port: $db_port"
    echo
    
    read -p "Proceed with this configuration? [Y/n]: " response
    response=${response:-Y}
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_warning "Configuration cancelled"
        return 1
    fi
    
    # Update authentication first
    update_pg_auth
    
    # Create database and user
    create_database_and_user "$db_name" "$db_user" "$db_password"
    
    # Test connection
    if test_connection "$db_name" "$db_user" "$db_password" "$db_host" "$db_port"; then
        print_success "Database configuration complete!"
    else
        print_warning "Connection test failed, attempting to fix..."
        
        # Try to fix connection issues
        fix_connection_issues "$db_name" "$db_user" "$db_password"
        
        # Retry connection
        if test_connection "$db_name" "$db_user" "$db_password" "$db_host" "$db_port"; then
            print_success "Connection fixed!"
        else
            print_error "Could not establish connection"
            print_info "Check $LOG_FILE for details"
            return 1
        fi
    fi
    
    # Save configuration
    save_configuration "$db_name" "$db_user" "$db_password" "$db_host" "$db_port"
    
    return 0
}

fix_connection_issues() {
    local db_name=$1
    local db_user=$2
    local db_password=$3
    
    print_step "Attempting to fix connection issues..."
    
    # Ensure user exists with correct password
    su - postgres -c "psql" << EOF >> "$LOG_FILE" 2>&1
ALTER USER $db_user WITH PASSWORD '$db_password';
ALTER USER $db_user WITH LOGIN;
GRANT CONNECT ON DATABASE $db_name TO $db_user;
GRANT ALL PRIVILEGES ON DATABASE $db_name TO $db_user;
EOF
    
    # Restart PostgreSQL to ensure all changes take effect
    print_debug "Restarting PostgreSQL..."
    if [ "$INIT_SYSTEM" = "sysvinit" ]; then
        service postgresql restart >> "$LOG_FILE" 2>&1 || true
    elif [ "$INIT_SYSTEM" = "systemd" ]; then
        systemctl restart postgresql >> "$LOG_FILE" 2>&1 || true
    else
        pkill -TERM postgres
        sleep 3
        start_postgresql
    fi
    
    sleep 3
}

save_configuration() {
    local db_name=$1
    local db_user=$2
    local db_password=$3
    local db_host=$4
    local db_port=$5
    
    print_step "Saving configuration..."
    
    # Create .env file
    cat > "$SCRIPT_DIR/.env" << EOF
# AutoTrainX PostgreSQL Configuration
# Generated on $(date)
AUTOTRAINX_DB_TYPE=postgresql
AUTOTRAINX_DB_HOST=$db_host
AUTOTRAINX_DB_PORT=$db_port
AUTOTRAINX_DB_NAME=$db_name
AUTOTRAINX_DB_USER=$db_user
AUTOTRAINX_DB_PASSWORD=$db_password
EOF
    
    chmod 600 "$SCRIPT_DIR/.env"
    print_success "Configuration saved to .env file"
    
    # Also create a connection string file
    cat > "$SCRIPT_DIR/.pgconnection" << EOF
# PostgreSQL connection string
postgresql://$db_user:$db_password@$db_host:$db_port/$db_name
EOF
    chmod 600 "$SCRIPT_DIR/.pgconnection"
}

# =====================================================
# Helper Scripts Creation
# =====================================================

create_helper_scripts() {
    print_step "Creating helper scripts..."
    
    # Start script
    cat > "$SCRIPT_DIR/start_postgresql_docker.sh" << 'EOF'
#!/bin/bash
# Start PostgreSQL in Docker container

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starting PostgreSQL...${NC}"

# Check if already running
if pg_isready -q 2>/dev/null || pgrep -f "postgres.*-D" > /dev/null; then
    echo -e "${GREEN}PostgreSQL is already running${NC}"
    exit 0
fi

# Find PostgreSQL version and paths
PG_VERSION=$(ls /usr/lib/postgresql/ 2>/dev/null | grep -E '^[0-9]+' | sort -V | tail -1)
if [ -z "$PG_VERSION" ]; then
    echo -e "${RED}Could not detect PostgreSQL version${NC}"
    exit 1
fi

PG_BIN="/usr/lib/postgresql/$PG_VERSION/bin"
PG_DATA="/var/lib/postgresql/$PG_VERSION/main"

# Try service first
if command -v service &> /dev/null; then
    service postgresql start 2>/dev/null
    sleep 3
    if pg_isready -q 2>/dev/null; then
        echo -e "${GREEN}PostgreSQL started with service command${NC}"
        exit 0
    fi
fi

# Direct start
echo "Starting PostgreSQL directly..."
mkdir -p /var/run/postgresql
chown postgres:postgres /var/run/postgresql

su - postgres -c "$PG_BIN/postgres -D $PG_DATA" >> /var/log/postgresql/startup.log 2>&1 &

# Wait for startup
count=0
while [ $count -lt 30 ]; do
    if pg_isready -q 2>/dev/null; then
        echo -e "${GREEN}PostgreSQL started successfully${NC}"
        exit 0
    fi
    sleep 1
    count=$((count + 1))
    echo -n "."
done
echo

echo -e "${RED}Failed to start PostgreSQL${NC}"
echo "Check /var/log/postgresql/startup.log for details"
exit 1
EOF
    chmod +x "$SCRIPT_DIR/start_postgresql_docker.sh"
    
    # Connection script
    cat > "$SCRIPT_DIR/connect_db.sh" << 'EOF'
#!/bin/bash
# Connect to AutoTrainX database

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Load environment
if [ -f "$SCRIPT_DIR/.env" ]; then
    source "$SCRIPT_DIR/.env"
fi

echo "Connecting to PostgreSQL database..."
echo "Host: ${AUTOTRAINX_DB_HOST:-localhost}"
echo "Database: ${AUTOTRAINX_DB_NAME:-autotrainx}"
echo "User: ${AUTOTRAINX_DB_USER:-autotrainx}"
echo

psql -h ${AUTOTRAINX_DB_HOST:-localhost} \
     -p ${AUTOTRAINX_DB_PORT:-5432} \
     -U ${AUTOTRAINX_DB_USER:-autotrainx} \
     -d ${AUTOTRAINX_DB_NAME:-autotrainx}
EOF
    chmod +x "$SCRIPT_DIR/connect_db.sh"
    
    # Status check script
    cat > "$SCRIPT_DIR/check_postgresql_status.sh" << 'EOF'
#!/bin/bash
# Check PostgreSQL status

echo "=== PostgreSQL Status Check ==="
echo

# Check if running
if pg_isready -q 2>/dev/null; then
    echo "✅ PostgreSQL is running"
    pg_isready
else
    echo "❌ PostgreSQL is not running"
fi

# Check processes
echo
echo "PostgreSQL processes:"
ps aux | grep postgres | grep -v grep

# Check port
echo
echo "Port 5432 status:"
ss -tlnp 2>/dev/null | grep 5432 || netstat -tlnp 2>/dev/null | grep 5432

# Check connections
echo
echo "Active connections:"
su - postgres -c "psql -c 'SELECT count(*) as connections FROM pg_stat_activity;'" 2>/dev/null || echo "Could not check connections"
EOF
    chmod +x "$SCRIPT_DIR/check_postgresql_status.sh"
    
    print_success "Helper scripts created"
}

# =====================================================
# Installation Function
# =====================================================

install_postgresql() {
    print_section "PostgreSQL Installation"
    
    if check_postgresql_installed; then
        print_success "PostgreSQL is already installed"
        print_info "Version: PostgreSQL $PG_VERSION"
        print_info "Binaries: $PG_BIN"
        return 0
    fi
    
    print_warning "PostgreSQL not found"
    read -p "Install PostgreSQL? [Y/n]: " response
    response=${response:-Y}
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_error "PostgreSQL is required"
        return 1
    fi
    
    print_step "Installing PostgreSQL..."
    
    # Update package list
    apt-get update >> "$LOG_FILE" 2>&1
    
    # Install PostgreSQL
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        postgresql \
        postgresql-contrib \
        postgresql-client \
        libpq-dev >> "$LOG_FILE" 2>&1
    
    if check_postgresql_installed; then
        print_success "PostgreSQL installed successfully"
        return 0
    else
        print_error "Failed to install PostgreSQL"
        return 1
    fi
}

# =====================================================
# Main Function
# =====================================================

main() {
    # Detect environment
    detect_environment
    
    # Show header
    print_header
    
    if [ "$IS_DOCKER" = true ]; then
        print_info "Docker container detected"
        print_info "Using Docker-optimized configuration"
    fi
    
    echo
    read -p "Continue with PostgreSQL setup? [Y/n]: " response
    response=${response:-Y}
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_warning "Setup cancelled"
        exit 0
    fi
    
    # Step 1: Install/verify PostgreSQL
    if ! install_postgresql; then
        print_error "Installation failed"
        print_info "Check $LOG_FILE for details"
        exit 1
    fi
    
    # Step 2: Configure PostgreSQL
    if ! configure_postgresql; then
        print_error "Configuration failed"
        print_info "Check $LOG_FILE for details"
        exit 1
    fi
    
    # Step 3: Create helper scripts
    create_helper_scripts
    
    # Done
    print_section "Setup Complete!"
    
    print_success "PostgreSQL has been configured for AutoTrainX"
    echo
    print_info "Configuration saved to:"
    echo "  - $SCRIPT_DIR/.env"
    echo "  - $SCRIPT_DIR/.pgconnection"
    echo
    print_info "Helper scripts created:"
    echo "  - ./start_postgresql_docker.sh - Start PostgreSQL"
    echo "  - ./connect_db.sh - Connect to database"
    echo "  - ./check_postgresql_status.sh - Check status"
    echo
    print_info "Logs saved to: $LOG_FILE"
    echo
    
    if [ "$IS_DOCKER" = true ]; then
        print_warning "In Docker: PostgreSQL must be started manually!"
        echo "Run: ./database_utils/start_postgresql_docker.sh"
    fi
}

# Run main function
main "$@"
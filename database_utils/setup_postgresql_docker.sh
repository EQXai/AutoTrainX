#!/bin/bash

# =====================================================
# AutoTrainX PostgreSQL Docker Setup Script
# =====================================================
# Version optimized for Docker containers
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

# Detect init system
INIT_SYSTEM="unknown"
if [ -d /run/systemd/system ]; then
    INIT_SYSTEM="systemd"
elif [ -f /var/run/supervisord.pid ]; then
    INIT_SYSTEM="supervisord"
elif command -v service &> /dev/null; then
    INIT_SYSTEM="sysvinit"
fi

# =====================================================
# Helper Functions
# =====================================================

print_header() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║   AutoTrainX PostgreSQL Setup (Docker Optimized)             ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -e "${YELLOW}Environment: ${IS_DOCKER:+Docker Container}${IS_DOCKER:-Host System}${NC}"
    echo -e "${YELLOW}Init System: $INIT_SYSTEM${NC}"
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

# Function to check if PostgreSQL is installed
check_postgresql_installed() {
    if command -v psql &> /dev/null && command -v postgres &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to check if PostgreSQL is running (Docker-aware)
check_postgresql_running() {
    # Try different methods based on environment
    if [ "$IS_DOCKER" = true ]; then
        # In Docker, check if postgres process is running
        if pgrep -x postgres > /dev/null 2>&1; then
            return 0
        fi
        
        # Check if we can connect to postgres
        if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
            return 0
        fi
    else
        # On host system, use systemctl
        if systemctl is-active --quiet postgresql 2>/dev/null; then
            return 0
        fi
    fi
    
    return 1
}

# Function to start PostgreSQL (Docker-aware)
start_postgresql() {
    print_step "Starting PostgreSQL..."
    
    if [ "$IS_DOCKER" = true ]; then
        # Find PostgreSQL data directory
        local PG_VERSION=$(ls /usr/lib/postgresql/ 2>/dev/null | grep -E '^[0-9]+' | sort -V | tail -1)
        local PG_DATA="/var/lib/postgresql/${PG_VERSION}/main"
        local PG_CONFIG="/etc/postgresql/${PG_VERSION}/main/postgresql.conf"
        
        # Check if PostgreSQL is initialized
        if [ ! -f "$PG_DATA/PG_VERSION" ]; then
            print_step "Initializing PostgreSQL cluster..."
            
            # Create directories
            mkdir -p "$PG_DATA"
            chown postgres:postgres "$PG_DATA"
            
            # Initialize cluster
            su - postgres -c "/usr/lib/postgresql/${PG_VERSION}/bin/initdb -D $PG_DATA"
            
            if [ $? -ne 0 ]; then
                print_error "Failed to initialize PostgreSQL cluster"
                return 1
            fi
        fi
        
        # Start PostgreSQL in background
        su - postgres -c "/usr/lib/postgresql/${PG_VERSION}/bin/postgres -D $PG_DATA -c config_file=$PG_CONFIG" &
        
        # Wait for PostgreSQL to start
        local count=0
        while [ $count -lt 30 ]; do
            if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
                print_success "PostgreSQL started successfully"
                return 0
            fi
            sleep 1
            count=$((count + 1))
        done
        
        print_error "Failed to start PostgreSQL"
        return 1
    else
        # Use systemctl on host system
        systemctl start postgresql
        systemctl enable postgresql
    fi
}

# Function to run psql as postgres user
run_psql_as_postgres() {
    su - postgres -c "psql -tAc \"$1\""
}

# Function to run psql commands
run_psql_commands() {
    su - postgres -c "psql" << EOF
$1
EOF
}

# =====================================================
# Installation Functions
# =====================================================

install_postgresql() {
    print_section "PostgreSQL Installation"
    
    if check_postgresql_installed; then
        print_success "PostgreSQL is already installed"
        local pg_version=$(psql --version | awk '{print $3}')
        print_info "PostgreSQL version: $pg_version"
        return 0
    fi
    
    print_info "PostgreSQL is not installed"
    echo
    read -p "Do you want to install PostgreSQL now? [Y/n]: " response
    response=${response:-Y}
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_error "PostgreSQL installation is required to continue"
        return 1
    fi
    
    print_step "Updating package list..."
    apt-get update
    
    print_step "Installing PostgreSQL and contrib package..."
    apt-get install -y postgresql postgresql-contrib
    
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
            print_error "Failed to start PostgreSQL"
            return 1
        fi
    fi
    
    # Get database configuration
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
    
    # Create user and database
    print_step "Creating database and user..."
    
    run_psql_commands "-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '$db_user') THEN
        CREATE USER $db_user WITH PASSWORD '$db_password';
    ELSE
        ALTER USER $db_user WITH PASSWORD '$db_password';
    END IF;
END
\$\$;

-- Create database if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db_name') THEN
        CREATE DATABASE $db_name OWNER $db_user;
    END IF;
END
\$\$;

-- Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE $db_name TO $db_user;"
    
    if [ $? -eq 0 ]; then
        print_success "Database and user created successfully"
    else
        print_error "Failed to create database and user"
        return 1
    fi
    
    # Update pg_hba.conf for password authentication
    print_step "Configuring authentication..."
    update_pg_hba_conf_docker
    
    # Test connection
    print_step "Testing database connection..."
    if PGPASSWORD="$db_password" psql -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" -c "SELECT 1;" &>/dev/null; then
        print_success "Database connection successful"
    else
        print_error "Failed to connect to database"
        return 1
    fi
    
    # Save configuration
    save_configuration "$db_name" "$db_user" "$db_password" "$db_host" "$db_port"
    
    return 0
}

update_pg_hba_conf_docker() {
    # Find PostgreSQL version
    local PG_VERSION=$(ls /usr/lib/postgresql/ 2>/dev/null | grep -E '^[0-9]+' | sort -V | tail -1)
    local pg_hba_conf="/etc/postgresql/${PG_VERSION}/main/pg_hba.conf"
    
    if [ ! -f "$pg_hba_conf" ]; then
        # Try to find it from running postgres
        pg_hba_conf=$(su - postgres -c "psql -tAc 'SHOW hba_file;'" 2>/dev/null | xargs)
    fi
    
    if [ -f "$pg_hba_conf" ]; then
        print_info "Found pg_hba.conf at: $pg_hba_conf"
        
        # Backup original
        cp "$pg_hba_conf" "$pg_hba_conf.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Update authentication methods
        sed -i 's/local   all             all                                     peer/local   all             all                                     md5/g' "$pg_hba_conf"
        sed -i 's/local   all             all                                     ident/local   all             all                                     md5/g' "$pg_hba_conf"
        
        # Reload PostgreSQL configuration
        if [ "$IS_DOCKER" = true ]; then
            # In Docker, send SIGHUP to postgres process
            pkill -HUP postgres
        else
            systemctl reload postgresql
        fi
        
        print_success "Authentication configuration updated"
    else
        print_warning "Could not find pg_hba.conf, skipping authentication update"
    fi
}

save_configuration() {
    local db_name=$1
    local db_user=$2
    local db_password=$3
    local db_host=$4
    local db_port=$5
    
    print_section "Save Configuration"
    
    # Create .env file
    print_step "Creating .env file..."
    
    cat > "$SCRIPT_DIR/.env" << EOF
# AutoTrainX PostgreSQL Configuration
AUTOTRAINX_DB_TYPE=postgresql
AUTOTRAINX_DB_HOST=$db_host
AUTOTRAINX_DB_PORT=$db_port
AUTOTRAINX_DB_NAME=$db_name
AUTOTRAINX_DB_USER=$db_user
AUTOTRAINX_DB_PASSWORD=$db_password
EOF
    
    chmod 600 "$SCRIPT_DIR/.env"
    print_success "Configuration saved to .env file"
    
    # Also export for current session
    export AUTOTRAINX_DB_TYPE=postgresql
    export AUTOTRAINX_DB_HOST=$db_host
    export AUTOTRAINX_DB_PORT=$db_port
    export AUTOTRAINX_DB_NAME=$db_name
    export AUTOTRAINX_DB_USER=$db_user
    export AUTOTRAINX_DB_PASSWORD=$db_password
    
    print_info "Environment variables set for current session"
}

# =====================================================
# Docker-specific startup script
# =====================================================

create_docker_startup_script() {
    print_step "Creating Docker startup script..."
    
    cat > "$SCRIPT_DIR/start_postgresql_docker.sh" << 'EOF'
#!/bin/bash

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starting PostgreSQL in Docker container...${NC}"

# Find PostgreSQL version
PG_VERSION=$(ls /usr/lib/postgresql/ 2>/dev/null | grep -E '^[0-9]+' | sort -V | tail -1)
PG_DATA="/var/lib/postgresql/${PG_VERSION}/main"
PG_CONFIG="/etc/postgresql/${PG_VERSION}/main/postgresql.conf"

# Check if PostgreSQL is already running
if pgrep -x postgres > /dev/null; then
    echo -e "${GREEN}PostgreSQL is already running${NC}"
    exit 0
fi

# Start PostgreSQL
su - postgres -c "/usr/lib/postgresql/${PG_VERSION}/bin/postgres -D $PG_DATA -c config_file=$PG_CONFIG" &

# Wait for PostgreSQL to be ready
count=0
while [ $count -lt 30 ]; do
    if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
        echo -e "${GREEN}PostgreSQL started successfully${NC}"
        exit 0
    fi
    sleep 1
    count=$((count + 1))
done

echo -e "${RED}Failed to start PostgreSQL${NC}"
exit 1
EOF
    
    chmod +x "$SCRIPT_DIR/start_postgresql_docker.sh"
    print_success "Docker startup script created"
}

# =====================================================
# Main setup function
# =====================================================

main() {
    print_header
    
    if [ "$IS_DOCKER" = true ]; then
        print_info "Detected Docker container environment"
        print_info "Using Docker-optimized configuration"
    else
        print_warning "This script is optimized for Docker containers"
        print_info "Running on host system - some features may work differently"
    fi
    
    echo
    read -p "Do you want to continue? [Y/n]: " response
    response=${response:-Y}
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_warning "Setup cancelled"
        exit 0
    fi
    
    # Step 1: Install PostgreSQL
    if ! install_postgresql; then
        print_error "Setup failed: PostgreSQL installation error"
        exit 1
    fi
    
    # Step 2: Configure PostgreSQL
    if ! configure_postgresql; then
        print_error "Setup failed: PostgreSQL configuration error"
        exit 1
    fi
    
    # Step 3: Create helper scripts
    create_docker_startup_script
    
    # Final summary
    print_section "Setup Complete!"
    
    print_success "PostgreSQL has been configured for AutoTrainX in Docker"
    echo
    print_info "Important notes for Docker:"
    echo "1. PostgreSQL needs to be started manually in containers"
    echo "2. Use: ./database_utils/start_postgresql_docker.sh"
    echo "3. Configuration saved in: ./database_utils/.env"
    echo "4. To connect: psql -h localhost -U $DEFAULT_DB_USER -d $DEFAULT_DB_NAME"
    echo
    
    if [ "$IS_DOCKER" = true ]; then
        print_warning "Remember to start PostgreSQL before running AutoTrainX!"
        echo "Add this to your container startup:"
        echo "  /path/to/database_utils/start_postgresql_docker.sh"
    fi
}

# Run main function
main
#!/bin/bash

# =====================================================
# AutoTrainX PostgreSQL Docker Interactive Menu
# =====================================================
# Optimized for Docker containers
# With arrow key navigation
# Based on lessons learned from previous attempts
# =====================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'
BOLD='\033[1m'
REVERSE='\033[7m'

# Configuration defaults
DEFAULT_DB_NAME="autotrainx"
DEFAULT_DB_USER="autotrainx"
DEFAULT_DB_PASSWORD="1234"
DEFAULT_DB_HOST="localhost"
DEFAULT_DB_PORT="5432"

# Global variables
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_FILE="$SCRIPT_DIR/postgresql_docker.log"
PG_VERSION=""
MENU_SELECTION=0

# Initialize log
echo "PostgreSQL Docker Setup Log - $(date)" > "$LOG_FILE"

# =====================================================
# Detection Functions
# =====================================================

detect_postgresql() {
    # Detect PostgreSQL version if installed
    if command -v psql &> /dev/null; then
        PG_VERSION=$(psql --version 2>/dev/null | grep -oE '[0-9]+' | head -1)
        echo "PostgreSQL detected via psql: version $PG_VERSION" >> "$LOG_FILE"
    elif dpkg -l 2>/dev/null | grep -q "postgresql-[0-9]"; then
        PG_VERSION=$(dpkg -l | grep "postgresql-[0-9]" | awk '{print $2}' | grep -oE '[0-9]+' | head -1)
        echo "PostgreSQL detected via dpkg: version $PG_VERSION" >> "$LOG_FILE"
    elif [ -d /usr/lib/postgresql ]; then
        PG_VERSION=$(ls /usr/lib/postgresql/ 2>/dev/null | grep -E '^[0-9]+' | sort -V | tail -1)
        echo "PostgreSQL detected in /usr/lib: version $PG_VERSION" >> "$LOG_FILE"
    fi
    
    # Set paths if version found
    if [ -n "$PG_VERSION" ]; then
        export PG_BIN="/usr/lib/postgresql/$PG_VERSION/bin"
        export PG_DATA="/var/lib/postgresql/$PG_VERSION/main"
        export PG_CONFIG="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
        export PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
    fi
}

# =====================================================
# UI Functions
# =====================================================

print_header() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║      AutoTrainX PostgreSQL Setup - Docker Edition            ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "${YELLOW}Environment: Docker Container${NC}"
    echo -e "${YELLOW}User: $(whoami)${NC}"
    [ -n "$PG_VERSION" ] && echo -e "${YELLOW}PostgreSQL: Version $PG_VERSION${NC}"
    echo -e "${YELLOW}Log: $LOG_FILE${NC}"
    echo
}

print_status() {
    local message=$1
    local type=$2
    
    case $type in
        "success") echo -e "${GREEN}✅ $message${NC}" ;;
        "error") echo -e "${RED}❌ $message${NC}" ;;
        "warning") echo -e "${YELLOW}⚠️  $message${NC}" ;;
        "info") echo -e "${BLUE}ℹ️  $message${NC}" ;;
        *) echo -e "${CYAN}▶️  $message${NC}" ;;
    esac
    
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $type: $message" >> "$LOG_FILE"
}

# Read single keypress for menu navigation
read_key() {
    local key
    IFS= read -rsn1 key 2>/dev/null >&2
    if [[ $key = $'\x1b' ]]; then
        read -rsn2 key 2>/dev/null >&2
        case $key in
            '[A') echo UP ;;
            '[B') echo DOWN ;;
            '[C') echo RIGHT ;;
            '[D') echo LEFT ;;
        esac
    else
        case $key in
            '') echo ENTER ;;
            q|Q) echo QUIT ;;
            *) echo "$key" ;;
        esac
    fi
}

# Draw menu with arrow navigation
draw_menu() {
    local title=$1
    shift
    local options=("$@")
    local num_options=${#options[@]}
    local selected=0
    
    # Hide cursor
    tput civis 2>/dev/null || true
    
    while true; do
        print_header
        echo -e "${BOLD}$title${NC}"
        echo -e "${BOLD}Use ↑/↓ arrows to navigate, Enter to select, Q to quit${NC}\n"
        
        # Draw menu options
        for ((i=0; i<num_options; i++)); do
            if [ $i -eq $selected ]; then
                echo -e "${REVERSE}▶ ${options[$i]}${NC}"
            else
                echo -e "  ${options[$i]}"
            fi
        done
        
        # Read user input
        local key=$(read_key)
        
        case $key in
            UP)
                ((selected--))
                [ $selected -lt 0 ] && selected=$((num_options - 1))
                ;;
            DOWN)
                ((selected++))
                [ $selected -ge $num_options ] && selected=0
                ;;
            ENTER)
                # Show cursor again
                tput cnorm 2>/dev/null || true
                return $selected
                ;;
            QUIT)
                # Show cursor again
                tput cnorm 2>/dev/null || true
                return 255
                ;;
        esac
    done
}

# =====================================================
# PostgreSQL Functions
# =====================================================

check_postgresql_installed() {
    print_status "Checking PostgreSQL installation..." "info"
    
    # Re-detect
    detect_postgresql
    
    if [ -n "$PG_VERSION" ]; then
        print_status "PostgreSQL $PG_VERSION is installed" "success"
        
        # Check binaries
        if [ -f "$PG_BIN/postgres" ]; then
            print_status "Binaries found at: $PG_BIN" "info"
        else
            print_status "Warning: Binaries not found at expected location" "warning"
        fi
        
        return 0
    else
        print_status "PostgreSQL not found" "warning"
        return 1
    fi
}

install_postgresql() {
    print_header
    echo -e "${BOLD}PostgreSQL Installation${NC}\n"
    
    if check_postgresql_installed; then
        print_status "PostgreSQL is already installed" "info"
        read -p "Press Enter to continue..."
        return 0
    fi
    
    print_status "Installing PostgreSQL..." "info"
    
    # Update package list
    print_status "Updating package list..." "info"
    apt-get update >> "$LOG_FILE" 2>&1 || {
        print_status "Failed to update package list" "error"
        read -p "Press Enter to continue..."
        return 1
    }
    
    # Install PostgreSQL
    print_status "Installing PostgreSQL packages..." "info"
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        postgresql postgresql-contrib postgresql-client >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        detect_postgresql  # Re-detect to get version
        print_status "PostgreSQL installed successfully" "success"
        
        # Initialize cluster if needed
        if [ ! -f "$PG_DATA/PG_VERSION" ]; then
            print_status "Initializing PostgreSQL cluster..." "info"
            mkdir -p "$PG_DATA"
            chown -R postgres:postgres /var/lib/postgresql
            su - postgres -c "$PG_BIN/initdb -D $PG_DATA" >> "$LOG_FILE" 2>&1
        fi
    else
        print_status "Failed to install PostgreSQL" "error"
        print_status "Check $LOG_FILE for details" "info"
    fi
    
    read -p "Press Enter to continue..."
}

start_postgresql_service() {
    print_header
    echo -e "${BOLD}Starting PostgreSQL Service${NC}\n"
    
    # Check if already running
    if pg_isready -q 2>/dev/null; then
        print_status "PostgreSQL is already running" "success"
        pg_isready
        read -p "Press Enter to continue..."
        return 0
    fi
    
    print_status "Starting PostgreSQL..." "info"
    
    # Method 1: service command
    if command -v service &> /dev/null; then
        print_status "Trying service command..." "info"
        service postgresql start >> "$LOG_FILE" 2>&1
        sleep 2
        
        if pg_isready -q 2>/dev/null; then
            print_status "PostgreSQL started successfully" "success"
            read -p "Press Enter to continue..."
            return 0
        fi
    fi
    
    # Method 2: Direct start
    if [ -n "$PG_VERSION" ] && [ -f "$PG_BIN/postgres" ]; then
        print_status "Trying direct start..." "info"
        
        # Ensure directories exist
        mkdir -p /var/run/postgresql
        chown postgres:postgres /var/run/postgresql
        
        # Start PostgreSQL
        su - postgres -c "$PG_BIN/postgres -D $PG_DATA" >> "$LOG_FILE" 2>&1 &
        
        # Wait for startup
        local count=0
        echo -n "Waiting for PostgreSQL to start"
        while [ $count -lt 30 ]; do
            if pg_isready -q 2>/dev/null; then
                echo
                print_status "PostgreSQL started successfully" "success"
                read -p "Press Enter to continue..."
                return 0
            fi
            sleep 1
            count=$((count + 1))
            echo -n "."
        done
        echo
    fi
    
    print_status "Failed to start PostgreSQL" "error"
    print_status "Check logs: $LOG_FILE" "info"
    read -p "Press Enter to continue..."
    return 1
}

configure_postgresql() {
    print_header
    echo -e "${BOLD}PostgreSQL Configuration${NC}\n"
    
    # Ensure PostgreSQL is running
    if ! pg_isready -q 2>/dev/null; then
        print_status "PostgreSQL is not running. Please start it first." "error"
        read -p "Press Enter to continue..."
        return 1
    fi
    
    # Get configuration
    echo -e "${BOLD}Enter database configuration:${NC}"
    read -p "Database name [$DEFAULT_DB_NAME]: " db_name
    db_name=${db_name:-$DEFAULT_DB_NAME}
    
    read -p "Database user [$DEFAULT_DB_USER]: " db_user
    db_user=${db_user:-$DEFAULT_DB_USER}
    
    read -sp "Database password [$DEFAULT_DB_PASSWORD]: " db_password
    db_password=${db_password:-$DEFAULT_DB_PASSWORD}
    echo
    
    print_status "Configuring PostgreSQL..." "info"
    
    # First, set trust authentication temporarily
    if [ -f "$PG_HBA" ]; then
        cp "$PG_HBA" "$PG_HBA.backup.$(date +%Y%m%d_%H%M%S)"
        cat > "$PG_HBA" << 'EOF'
# Temporary trust authentication
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
EOF
        service postgresql reload 2>/dev/null || pkill -HUP postgres
        sleep 2
    fi
    
    # Create user and database using psql directly
    print_status "Creating user and database..." "info"
    
    psql -U postgres >> "$LOG_FILE" 2>&1 << EOF
-- Create user
CREATE USER $db_user WITH PASSWORD '$db_password';
-- Create database
CREATE DATABASE $db_name OWNER $db_user;
-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $db_name TO $db_user;
EOF
    
    # Set secure authentication
    if [ -f "$PG_HBA" ]; then
        cat > "$PG_HBA" << 'EOF'
# PostgreSQL Client Authentication
local   all             postgres                                peer
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
EOF
        service postgresql reload 2>/dev/null || pkill -HUP postgres
        sleep 2
    fi
    
    # Test connection
    print_status "Testing connection..." "info"
    export PGPASSWORD="$db_password"
    
    if psql -h localhost -U "$db_user" -d "$db_name" -c "SELECT 'Connected successfully' as status;" 2>/dev/null; then
        print_status "Configuration successful!" "success"
        
        # Save configuration
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
        print_status "Configuration saved to .env" "success"
    else
        print_status "Configuration failed - connection test unsuccessful" "error"
    fi
    
    unset PGPASSWORD
    read -p "Press Enter to continue..."
}

test_connection() {
    print_header
    echo -e "${BOLD}Test Database Connection${NC}\n"
    
    # Check if PostgreSQL is running first
    if ! pg_isready -q 2>/dev/null; then
        print_status "PostgreSQL is not running!" "error"
        echo "Please start PostgreSQL first."
        read -p "Press Enter to continue..."
        return
    fi
    
    # Load configuration
    if [ -f "$SCRIPT_DIR/.env" ]; then
        source "$SCRIPT_DIR/.env"
        
        print_status "Testing connection to:" "info"
        echo "  Host: ${AUTOTRAINX_DB_HOST}"
        echo "  Port: ${AUTOTRAINX_DB_PORT}"
        echo "  Database: ${AUTOTRAINX_DB_NAME}"
        echo "  User: ${AUTOTRAINX_DB_USER}"
        echo
        
        export PGPASSWORD="${AUTOTRAINX_DB_PASSWORD}"
        
        # Test connection with detailed output
        if psql -h "${AUTOTRAINX_DB_HOST}" -p "${AUTOTRAINX_DB_PORT}" \
               -U "${AUTOTRAINX_DB_USER}" -d "${AUTOTRAINX_DB_NAME}" \
               -c "SELECT version();" 2>&1; then
            echo
            print_status "Connection successful!" "success"
            
            # Show database info
            echo
            echo -e "${BOLD}Database Information:${NC}"
            psql -h "${AUTOTRAINX_DB_HOST}" -p "${AUTOTRAINX_DB_PORT}" \
                 -U "${AUTOTRAINX_DB_USER}" -d "${AUTOTRAINX_DB_NAME}" << EOF
SELECT 
    current_database() as "Database",
    current_user as "User",
    pg_size_pretty(pg_database_size(current_database())) as "Size";
SELECT COUNT(*) as "Tables" FROM pg_tables WHERE schemaname = 'public';
EOF
        else
            print_status "Connection failed" "error"
            echo
            echo "Troubleshooting tips:"
            echo "1. Check if PostgreSQL is running: pg_isready"
            echo "2. Verify credentials in .env file"
            echo "3. Check pg_hba.conf authentication settings"
            echo "4. Try: psql -U postgres (should work with trust auth)"
        fi
        
        unset PGPASSWORD
    else
        print_status "No configuration found. Please configure first." "warning"
    fi
    
    echo
    read -p "Press Enter to continue..."
}

view_postgresql_status() {
    print_header
    echo -e "${BOLD}PostgreSQL Status${NC}\n"
    
    # Service status
    echo -e "${BOLD}Service Status:${NC}"
    if pg_isready 2>/dev/null; then
        print_status "PostgreSQL is running" "success"
        pg_isready
    else
        print_status "PostgreSQL is not running" "error"
    fi
    
    # Version and paths
    if [ -n "$PG_VERSION" ]; then
        echo -e "\n${BOLD}Installation Details:${NC}"
        echo "Version: PostgreSQL $PG_VERSION"
        echo "Binaries: $PG_BIN"
        echo "Data: $PG_DATA"
        echo "Config: $PG_CONFIG"
        echo "HBA: $PG_HBA"
    fi
    
    # Process info
    echo -e "\n${BOLD}PostgreSQL Processes:${NC}"
    ps aux | grep postgres | grep -v grep | head -5 || echo "No PostgreSQL processes found"
    
    # Port status
    echo -e "\n${BOLD}Port 5432 Status:${NC}"
    ss -tlnp 2>/dev/null | grep 5432 || netstat -tlnp 2>/dev/null | grep 5432 || echo "Port check requires root privileges"
    
    # Disk usage
    if [ -d "$PG_DATA" ]; then
        echo -e "\n${BOLD}Data Directory Size:${NC}"
        du -sh "$PG_DATA" 2>/dev/null || echo "Cannot check size"
    fi
    
    # Configuration status
    echo -e "\n${BOLD}Configuration Files:${NC}"
    [ -f "$PG_CONFIG" ] && echo "✓ postgresql.conf exists" || echo "✗ postgresql.conf not found"
    [ -f "$PG_HBA" ] && echo "✓ pg_hba.conf exists" || echo "✗ pg_hba.conf not found"
    [ -f "$SCRIPT_DIR/.env" ] && echo "✓ .env exists" || echo "✗ .env not found"
    
    echo
    read -p "Press Enter to continue..."
}

quick_fix_auth() {
    print_header
    echo -e "${BOLD}Quick Fix Authentication${NC}\n"
    
    print_status "This will reset PostgreSQL authentication to allow easy access" "warning"
    echo "Use this if you're having authentication problems."
    echo
    read -p "Continue? [y/N]: " confirm
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        return
    fi
    
    detect_postgresql
    
    if [ ! -f "$PG_HBA" ]; then
        print_status "Cannot find pg_hba.conf" "error"
        read -p "Press Enter to continue..."
        return
    fi
    
    # Backup current configuration
    cp "$PG_HBA" "$PG_HBA.backup.quickfix.$(date +%Y%m%d_%H%M%S)"
    print_status "Backed up current pg_hba.conf" "info"
    
    # Set trust authentication
    cat > "$PG_HBA" << 'EOF'
# Trust authentication - NO PASSWORD REQUIRED
# This is temporary for fixing issues
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
EOF
    
    # Reload PostgreSQL
    print_status "Applying trust authentication..." "info"
    service postgresql reload 2>/dev/null || pkill -HUP postgres
    sleep 2
    
    print_status "Trust authentication enabled!" "success"
    echo
    echo -e "${YELLOW}⚠️  WARNING: PostgreSQL now accepts connections without password!${NC}"
    echo
    echo "You can now:"
    echo "1. Connect as any user: psql -U postgres"
    echo "2. Reset passwords: ALTER USER username WITH PASSWORD 'newpass';"
    echo "3. Create users/databases without authentication issues"
    echo
    echo "To restore secure authentication later:"
    echo "  cp $PG_HBA.backup.quickfix.* $PG_HBA"
    echo "  service postgresql reload"
    
    read -p "Press Enter to continue..."
}

create_helper_scripts() {
    print_header
    echo -e "${BOLD}Creating Helper Scripts${NC}\n"
    
    # Start script
    cat > "$SCRIPT_DIR/start_pg_docker.sh" << 'EOF'
#!/bin/bash
# Start PostgreSQL in Docker
echo "Starting PostgreSQL..."
service postgresql start 2>/dev/null || {
    PG_VER=$(ls /usr/lib/postgresql/ | grep -E '^[0-9]+' | head -1)
    su - postgres -c "/usr/lib/postgresql/$PG_VER/bin/postgres -D /var/lib/postgresql/$PG_VER/main" &
}
sleep 2
pg_isready && echo "PostgreSQL started successfully" || echo "Failed to start PostgreSQL"
EOF
    chmod +x "$SCRIPT_DIR/start_pg_docker.sh"
    
    # Connect script
    if [ -f "$SCRIPT_DIR/.env" ]; then
        source "$SCRIPT_DIR/.env"
        cat > "$SCRIPT_DIR/connect_pg.sh" << EOF
#!/bin/bash
# Connect to PostgreSQL
export PGPASSWORD='${AUTOTRAINX_DB_PASSWORD}'
psql -h localhost -U ${AUTOTRAINX_DB_USER} -d ${AUTOTRAINX_DB_NAME}
EOF
        chmod +x "$SCRIPT_DIR/connect_pg.sh"
    fi
    
    # Status script
    cat > "$SCRIPT_DIR/pg_status.sh" << 'EOF'
#!/bin/bash
# Check PostgreSQL status
echo "PostgreSQL Status:"
pg_isready || echo "PostgreSQL is not running"
echo
echo "Processes:"
ps aux | grep postgres | grep -v grep
EOF
    chmod +x "$SCRIPT_DIR/pg_status.sh"
    
    print_status "Helper scripts created:" "success"
    echo "  - start_pg_docker.sh : Start PostgreSQL"
    [ -f "$SCRIPT_DIR/connect_pg.sh" ] && echo "  - connect_pg.sh : Connect to database"
    echo "  - pg_status.sh : Check status"
    
    read -p "Press Enter to continue..."
}

show_logs() {
    print_header
    echo -e "${BOLD}View Logs${NC}\n"
    
    echo "Recent setup log entries:"
    echo "========================="
    tail -20 "$LOG_FILE"
    
    echo
    echo "PostgreSQL logs (if available):"
    echo "==============================="
    
    # Try to find PostgreSQL logs
    local pg_log_dir="/var/log/postgresql"
    if [ -d "$pg_log_dir" ]; then
        local latest_log=$(ls -t "$pg_log_dir"/*.log 2>/dev/null | head -1)
        if [ -f "$latest_log" ]; then
            tail -20 "$latest_log"
        else
            echo "No PostgreSQL logs found in $pg_log_dir"
        fi
    else
        echo "PostgreSQL log directory not found"
    fi
    
    echo
    read -p "Press Enter to continue..."
}

# =====================================================
# Main Menu
# =====================================================

main_menu() {
    while true; do
        local options=(
            "🔍 View PostgreSQL Status"
            "📦 Install PostgreSQL"
            "🚀 Start PostgreSQL Service"
            "⚙️  Configure Database (Create user/db)"
            "🧪 Test Database Connection"
            "🔧 Quick Fix Authentication"
            "📝 Create Helper Scripts"
            "📊 View Logs"
            "❌ Exit"
        )
        
        draw_menu "PostgreSQL Docker Setup - Main Menu" "${options[@]}"
        local choice=$?
        
        case $choice in
            0) view_postgresql_status ;;
            1) install_postgresql ;;
            2) start_postgresql_service ;;
            3) configure_postgresql ;;
            4) test_connection ;;
            5) quick_fix_auth ;;
            6) create_helper_scripts ;;
            7) show_logs ;;
            8|255) 
                echo
                print_status "Exiting..." "info"
                # Show cursor
                tput cnorm 2>/dev/null || true
                exit 0 
                ;;
        esac
    done
}

# =====================================================
# Script Entry Point
# =====================================================

# Initial detection
detect_postgresql

# Check if running in Docker
if [ ! -f /.dockerenv ] && ! grep -q docker /proc/1/cgroup 2>/dev/null; then
    print_header
    print_status "This script is optimized for Docker containers" "warning"
    print_status "Running on a regular system may have different behavior" "info"
    echo
    read -p "Continue anyway? [y/N]: " confirm
    [[ ! "$confirm" =~ ^[Yy]$ ]] && exit 0
fi

# Start main menu
main_menu
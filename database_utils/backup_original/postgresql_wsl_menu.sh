#!/bin/bash

# =====================================================
# AutoTrainX PostgreSQL WSL Interactive Menu
# =====================================================
# Optimized for WSL/Docker environments
# With arrow key navigation
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
LOG_FILE="$SCRIPT_DIR/postgresql_wsl.log"
IS_WSL=false
IS_DOCKER=false
PG_VERSION=""
MENU_SELECTION=0

# Initialize log
echo "PostgreSQL WSL Setup Log - $(date)" > "$LOG_FILE"

# =====================================================
# Detection Functions
# =====================================================

detect_environment() {
    # Detect WSL
    if grep -qi microsoft /proc/version 2>/dev/null; then
        IS_WSL=true
        echo "WSL environment detected" >> "$LOG_FILE"
    fi
    
    # Detect Docker
    if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
        IS_DOCKER=true
        echo "Docker environment detected" >> "$LOG_FILE"
    fi
    
    # Detect PostgreSQL version if installed
    if command -v psql &> /dev/null; then
        PG_VERSION=$(psql --version 2>/dev/null | grep -oE '[0-9]+' | head -1)
    elif dpkg -l | grep -q "postgresql-[0-9]"; then
        PG_VERSION=$(dpkg -l | grep "postgresql-[0-9]" | awk '{print $2}' | grep -oE '[0-9]+' | head -1)
    elif [ -d /usr/lib/postgresql ]; then
        PG_VERSION=$(ls /usr/lib/postgresql/ 2>/dev/null | grep -E '^[0-9]+' | sort -V | tail -1)
    fi
}

# =====================================================
# UI Functions
# =====================================================

print_header() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║     AutoTrainX PostgreSQL Setup - WSL/Docker Edition         ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Environment info
    local env_info=""
    [ "$IS_WSL" = true ] && env_info="WSL"
    [ "$IS_DOCKER" = true ] && env_info="${env_info:+$env_info/}Docker"
    [ -z "$env_info" ] && env_info="Standard Linux"
    
    echo -e "${YELLOW}Environment: $env_info${NC}"
    echo -e "${YELLOW}User: $(whoami)${NC}"
    [ -n "$PG_VERSION" ] && echo -e "${YELLOW}PostgreSQL: Version $PG_VERSION detected${NC}"
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
    tput civis
    
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
                tput cnorm
                return $selected
                ;;
            QUIT)
                # Show cursor again
                tput cnorm
                return 255
                ;;
        esac
    done
}

# =====================================================
# PostgreSQL Management Functions
# =====================================================

check_postgresql_installed() {
    print_status "Checking PostgreSQL installation..." "info"
    
    # Multiple detection methods
    if command -v psql &> /dev/null && command -v postgres &> /dev/null; then
        print_status "PostgreSQL is installed (commands found)" "success"
        return 0
    fi
    
    if dpkg -l | grep -q "postgresql"; then
        print_status "PostgreSQL packages detected" "success"
        return 0
    fi
    
    if [ -d "/usr/lib/postgresql/$PG_VERSION" ] && [ -n "$PG_VERSION" ]; then
        print_status "PostgreSQL $PG_VERSION found in /usr/lib" "success"
        return 0
    fi
    
    print_status "PostgreSQL not found" "warning"
    return 1
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
    apt-get update >> "$LOG_FILE" 2>&1
    
    # Install PostgreSQL
    print_status "Installing PostgreSQL packages..." "info"
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        postgresql postgresql-contrib postgresql-client >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        detect_environment  # Re-detect to get version
        print_status "PostgreSQL installed successfully" "success"
    else
        print_status "Failed to install PostgreSQL" "error"
        print_status "Check $LOG_FILE for details" "info"
    fi
    
    read -p "Press Enter to continue..."
}

start_postgresql_service() {
    print_status "Starting PostgreSQL..." "info"
    
    # Check if already running
    if pg_isready -q 2>/dev/null; then
        print_status "PostgreSQL is already running" "success"
        return 0
    fi
    
    # Try different start methods
    if command -v service &> /dev/null; then
        service postgresql start >> "$LOG_FILE" 2>&1
        sleep 2
        if pg_isready -q 2>/dev/null; then
            print_status "PostgreSQL started with service command" "success"
            return 0
        fi
    fi
    
    # Try systemctl (might work in WSL2)
    if command -v systemctl &> /dev/null && [ "$IS_WSL" = true ]; then
        systemctl start postgresql >> "$LOG_FILE" 2>&1 || true
        sleep 2
        if pg_isready -q 2>/dev/null; then
            print_status "PostgreSQL started with systemctl" "success"
            return 0
        fi
    fi
    
    # Direct start as last resort
    if [ -n "$PG_VERSION" ]; then
        print_status "Attempting direct start..." "warning"
        local pg_bin="/usr/lib/postgresql/$PG_VERSION/bin"
        local pg_data="/var/lib/postgresql/$PG_VERSION/main"
        
        if [ -d "$pg_bin" ] && [ -d "$pg_data" ]; then
            su - postgres -c "$pg_bin/postgres -D $pg_data" >> "$LOG_FILE" 2>&1 &
            sleep 3
            if pg_isready -q 2>/dev/null; then
                print_status "PostgreSQL started directly" "success"
                return 0
            fi
        fi
    fi
    
    print_status "Failed to start PostgreSQL" "error"
    return 1
}

configure_postgresql() {
    print_header
    echo -e "${BOLD}PostgreSQL Configuration${NC}\n"
    
    # Ensure PostgreSQL is running
    if ! pg_isready -q 2>/dev/null; then
        print_status "PostgreSQL is not running. Starting..." "warning"
        start_postgresql_service || {
            print_status "Cannot proceed without PostgreSQL running" "error"
            read -p "Press Enter to continue..."
            return 1
        }
    fi
    
    # Get configuration
    echo -e "${BOLD}Database Configuration:${NC}"
    read -p "Database name [$DEFAULT_DB_NAME]: " db_name
    db_name=${db_name:-$DEFAULT_DB_NAME}
    
    read -p "Database user [$DEFAULT_DB_USER]: " db_user
    db_user=${db_user:-$DEFAULT_DB_USER}
    
    read -sp "Database password [$DEFAULT_DB_PASSWORD]: " db_password
    db_password=${db_password:-$DEFAULT_DB_PASSWORD}
    echo
    
    print_status "Configuring PostgreSQL..." "info"
    
    # Fix authentication first
    fix_pg_authentication
    
    # Create user and database
    print_status "Creating user and database..." "info"
    
    # Use trust auth temporarily
    psql -U postgres >> "$LOG_FILE" 2>&1 << EOF
CREATE USER $db_user WITH PASSWORD '$db_password';
CREATE DATABASE $db_name OWNER $db_user;
GRANT ALL PRIVILEGES ON DATABASE $db_name TO $db_user;
EOF
    
    # Test connection
    export PGPASSWORD="$db_password"
    if psql -h localhost -U "$db_user" -d "$db_name" -c "SELECT 1;" >> "$LOG_FILE" 2>&1; then
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
        print_status "Configuration saved to .env" "success"
    else
        print_status "Configuration failed" "error"
    fi
    unset PGPASSWORD
    
    read -p "Press Enter to continue..."
}

fix_pg_authentication() {
    local pg_hba="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
    
    if [ ! -f "$pg_hba" ]; then
        pg_hba=$(find /etc/postgresql -name pg_hba.conf 2>/dev/null | head -1)
    fi
    
    if [ -f "$pg_hba" ]; then
        # Backup
        cp "$pg_hba" "$pg_hba.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Set trust temporarily for setup
        cat > "$pg_hba" << 'EOF'
# Temporary trust for setup
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
EOF
        
        # Reload
        if command -v service &> /dev/null; then
            service postgresql reload >> "$LOG_FILE" 2>&1
        else
            pkill -HUP postgres 2>/dev/null
        fi
        sleep 1
        
        # Schedule restoration of secure auth
        (
            sleep 5
            cat > "$pg_hba" << 'EOF'
# PostgreSQL Client Authentication
local   all             postgres                                peer
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
EOF
            if command -v service &> /dev/null; then
                service postgresql reload >> "$LOG_FILE" 2>&1
            else
                pkill -HUP postgres 2>/dev/null
            fi
        ) &
    fi
}

test_connection() {
    print_header
    echo -e "${BOLD}Test Database Connection${NC}\n"
    
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
        
        # Test connection
        if psql -h "${AUTOTRAINX_DB_HOST}" -p "${AUTOTRAINX_DB_PORT}" \
               -U "${AUTOTRAINX_DB_USER}" -d "${AUTOTRAINX_DB_NAME}" \
               -c "SELECT version();" 2>/dev/null; then
            print_status "Connection successful!" "success"
            
            # Show some stats
            echo
            psql -h "${AUTOTRAINX_DB_HOST}" -p "${AUTOTRAINX_DB_PORT}" \
                 -U "${AUTOTRAINX_DB_USER}" -d "${AUTOTRAINX_DB_NAME}" << EOF
SELECT 'Database Size' as metric, pg_size_pretty(pg_database_size(current_database())) as value
UNION ALL
SELECT 'Tables', COUNT(*)::text FROM pg_tables WHERE schemaname = 'public';
EOF
        else
            print_status "Connection failed" "error"
            print_status "Check if PostgreSQL is running: pg_isready" "info"
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
    
    # Version info
    echo -e "\n${BOLD}Version Information:${NC}"
    if [ -n "$PG_VERSION" ]; then
        echo "Installed version: PostgreSQL $PG_VERSION"
        [ -f "/usr/lib/postgresql/$PG_VERSION/bin/postgres" ] && \
            echo "Binary: /usr/lib/postgresql/$PG_VERSION/bin/postgres"
    fi
    
    # Process info
    echo -e "\n${BOLD}PostgreSQL Processes:${NC}"
    ps aux | grep postgres | grep -v grep | head -5
    
    # Port status
    echo -e "\n${BOLD}Port Status:${NC}"
    ss -tlnp 2>/dev/null | grep 5432 || netstat -tlnp 2>/dev/null | grep 5432 || \
        echo "Cannot check port status (try with sudo)"
    
    # Configuration files
    echo -e "\n${BOLD}Configuration Files:${NC}"
    [ -f "/etc/postgresql/$PG_VERSION/main/postgresql.conf" ] && \
        echo "✓ /etc/postgresql/$PG_VERSION/main/postgresql.conf"
    [ -f "/etc/postgresql/$PG_VERSION/main/pg_hba.conf" ] && \
        echo "✓ /etc/postgresql/$PG_VERSION/main/pg_hba.conf"
    [ -f "$SCRIPT_DIR/.env" ] && \
        echo "✓ $SCRIPT_DIR/.env (AutoTrainX config)"
    
    echo
    read -p "Press Enter to continue..."
}

quick_fix_auth() {
    print_header
    echo -e "${BOLD}Quick Fix Authentication${NC}\n"
    
    print_status "This will temporarily set trust authentication to fix access issues" "warning"
    read -p "Continue? [y/N]: " confirm
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        return
    fi
    
    # Run the fix script logic
    local pg_hba="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
    
    if [ -f "$pg_hba" ]; then
        cp "$pg_hba" "$pg_hba.backup.quickfix"
        
        # Set trust auth
        cat > "$pg_hba" << 'EOF'
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
EOF
        
        # Reload
        service postgresql reload 2>/dev/null || pkill -HUP postgres
        sleep 1
        
        print_status "Trust authentication enabled" "success"
        print_status "You can now connect without password" "info"
        print_status "Remember to restore secure authentication after fixing issues!" "warning"
        
        echo
        echo "To restore secure auth later:"
        echo "  cp $pg_hba.backup.quickfix $pg_hba"
        echo "  service postgresql reload"
    else
        print_status "Could not find pg_hba.conf" "error"
    fi
    
    echo
    read -p "Press Enter to continue..."
}

show_help() {
    print_header
    echo -e "${BOLD}Help & Troubleshooting${NC}\n"
    
    cat << 'EOF'
COMMON ISSUES AND SOLUTIONS:

1. PostgreSQL won't start in WSL:
   - WSL1: Use 'service postgresql start'
   - WSL2: Enable systemd or use direct start
   - Check logs: /var/log/postgresql/*.log

2. Authentication failed:
   - Use "Quick Fix Authentication" from menu
   - Check pg_hba.conf settings
   - Ensure password is correct

3. Connection refused:
   - Check if PostgreSQL is running: pg_isready
   - Verify port 5432 is not blocked
   - Check listen_addresses in postgresql.conf

4. Permission denied:
   - Run this script with sudo if needed
   - Check file ownership: chown postgres:postgres /var/lib/postgresql

5. In Docker containers:
   - PostgreSQL doesn't persist after restart
   - Add startup script to container
   - Mount volumes for data persistence

USEFUL COMMANDS:

Start PostgreSQL:
  service postgresql start

Connect to database:
  psql -U postgres
  psql -h localhost -U autotrainx -d autotrainx

Check status:
  pg_isready
  service postgresql status

View logs:
  tail -f /var/log/postgresql/*.log

EOF
    
    read -p "Press Enter to continue..."
}

# =====================================================
# Main Menu
# =====================================================

main_menu() {
    while true; do
        local options=(
            "🔍 Check PostgreSQL Status"
            "📦 Install PostgreSQL"
            "🚀 Start PostgreSQL Service"
            "⚙️  Configure Database (Create user/database)"
            "🧪 Test Database Connection"
            "🔧 Quick Fix Authentication"
            "📚 Help & Troubleshooting"
            "❌ Exit"
        )
        
        draw_menu "Main Menu - Select an option:" "${options[@]}"
        local choice=$?
        
        case $choice in
            0) view_postgresql_status ;;
            1) install_postgresql ;;
            2) start_postgresql_service; read -p "Press Enter to continue..." ;;
            3) configure_postgresql ;;
            4) test_connection ;;
            5) quick_fix_auth ;;
            6) show_help ;;
            7|255) 
                echo
                print_status "Exiting..." "info"
                exit 0 
                ;;
        esac
    done
}

# =====================================================
# Script Entry Point
# =====================================================

# Detect environment
detect_environment

# Check if running as root (recommended for PostgreSQL setup)
if [ "$(id -u)" -ne 0 ] && [ "$1" != "--no-root-check" ]; then
    print_header
    print_status "This script is recommended to run as root for PostgreSQL setup" "warning"
    print_status "Run with --no-root-check to skip this warning" "info"
    echo
    read -p "Continue anyway? [y/N]: " confirm
    [[ ! "$confirm" =~ ^[Yy]$ ]] && exit 0
fi

# Start main menu
main_menu
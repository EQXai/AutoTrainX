#!/bin/bash

# =====================================================
# AutoTrainX PostgreSQL Interactive Setup Script
# =====================================================
# Enhanced version with arrow key navigation and
# organized table viewing
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
REVERSE='\033[7m'

# Default values
DEFAULT_DB_NAME="autotrainx"
DEFAULT_DB_USER="autotrainx"
DEFAULT_DB_PASSWORD="1234"
DEFAULT_DB_HOST="localhost"
DEFAULT_DB_PORT="5432"

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Global variables for menu navigation
MENU_SELECTION=0
MENU_SIZE=0

# =====================================================
# Helper Functions
# =====================================================

print_header() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║       AutoTrainX PostgreSQL Interactive Setup                 ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
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

# =====================================================
# Navigation Functions
# =====================================================

# Read single keypress
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
            '[H') echo HOME ;;
            '[F') echo END ;;
        esac
    else
        case $key in
            '') echo ENTER ;;
            $'\x7f') echo BACKSPACE ;;
            'q'|'Q') echo QUIT ;;
            *) echo "$key" ;;
        esac
    fi
}

# Draw menu with arrow navigation
draw_menu() {
    local options=("$@")
    local num_options=${#options[@]}
    local selected=0
    local key
    
    # Hide cursor
    tput civis
    
    while true; do
        # Clear screen and show header
        clear
        print_header
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
        key=$(read_key)
        
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
# Database Table Functions
# =====================================================

get_table_list() {
    local host=$1
    local port=$2
    local user=$3
    local pass=$4
    local db=$5
    
    PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" -t -A -c \
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
}

show_table_details() {
    local host=$1
    local port=$2
    local user=$3
    local pass=$4
    local db=$5
    local table=$6
    
    clear
    print_header
    print_section "Table: $table"
    
    # Table structure
    echo -e "${BOLD}Table Structure:${NC}"
    PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" -c "\d $table"
    
    echo
    
    # Table stats
    echo -e "${BOLD}Table Statistics:${NC}"
    PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" << EOF
SELECT 
    'Total Records' as metric,
    COUNT(*)::text as value
FROM $table
UNION ALL
SELECT 
    'Table Size',
    pg_size_pretty(pg_total_relation_size('$table'))
UNION ALL
SELECT 
    'Row Estimate',
    to_char(reltuples, 'FM999,999,999,999') 
FROM pg_class 
WHERE relname = '$table';
EOF
    
    echo
    echo -e "${BOLD}Sample Data (first 10 rows):${NC}"
    PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" -c \
        "SELECT * FROM $table LIMIT 10;"
    
    echo
    read -p "Press Enter to continue..."
}

interactive_table_browser() {
    local host=$1
    local port=$2
    local user=$3
    local pass=$4
    local db=$5
    
    while true; do
        # Get list of tables
        local tables=($(get_table_list "$host" "$port" "$user" "$pass" "$db"))
        
        if [ ${#tables[@]} -eq 0 ]; then
            print_error "No tables found in database"
            read -p "Press Enter to continue..."
            return
        fi
        
        # Add options
        local menu_options=()
        for table in "${tables[@]}"; do
            local count=$(PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" -t -A -c \
                "SELECT COUNT(*) FROM $table;")
            local size=$(PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" -t -A -c \
                "SELECT pg_size_pretty(pg_total_relation_size('$table'));")
            menu_options+=("$table (${count} records, ${size})")
        done
        menu_options+=("← Back to Main Menu")
        
        # Show menu
        draw_menu "${menu_options[@]}"
        local choice=$?
        
        # Handle quit
        if [ $choice -eq 255 ]; then
            return
        fi
        
        # Handle selection
        if [ $choice -eq ${#tables[@]} ]; then
            # Back option
            return
        else
            # Show table details
            show_table_details "$host" "$port" "$user" "$pass" "$db" "${tables[$choice]}"
        fi
    done
}

# =====================================================
# Enhanced Test Connection Function
# =====================================================

test_connection_enhanced() {
    print_section "Database Connection Test"
    
    source ~/.bashrc 2>/dev/null || true
    
    local host=${AUTOTRAINX_DB_HOST:-localhost}
    local port=${AUTOTRAINX_DB_PORT:-5432}
    local user=${AUTOTRAINX_DB_USER:-autotrainx}
    local pass=${AUTOTRAINX_DB_PASSWORD:-1234}
    local db=${AUTOTRAINX_DB_NAME:-autotrainx}
    
    print_info "Testing connection to:"
    echo "  Host: $host:$port"
    echo "  Database: $db"
    echo "  User: $user"
    echo
    
    if ! PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" -c "SELECT 1;" &>/dev/null; then
        print_error "Connection failed"
        print_info "Check your configuration and try again"
        read -p "Press Enter to continue..."
        return 1
    fi
    
    print_success "Connection successful!"
    echo
    
    # Show connection menu
    local options=(
        "View Database Summary"
        "Browse Tables Interactively"
        "Run Custom Query"
        "Export Table Data"
        "← Back to Main Menu"
    )
    
    while true; do
        draw_menu "${options[@]}"
        local choice=$?
        
        case $choice in
            0)  # View Database Summary
                show_database_summary "$host" "$port" "$user" "$pass" "$db"
                ;;
            1)  # Browse Tables
                interactive_table_browser "$host" "$port" "$user" "$pass" "$db"
                ;;
            2)  # Run Custom Query
                run_custom_query "$host" "$port" "$user" "$pass" "$db"
                ;;
            3)  # Export Table Data
                export_table_data "$host" "$port" "$user" "$pass" "$db"
                ;;
            4|255)  # Back or Quit
                return
                ;;
        esac
    done
}

show_database_summary() {
    local host=$1
    local port=$2
    local user=$3
    local pass=$4
    local db=$5
    
    clear
    print_header
    print_section "Database Summary"
    
    PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" << EOF
-- Database Info
SELECT 
    current_database() as "Database",
    pg_size_pretty(pg_database_size(current_database())) as "Total Size",
    (SELECT count(*) FROM pg_tables WHERE schemaname = 'public') as "Tables",
    version() as "PostgreSQL Version"
\gx

-- Tables Overview
\echo
\echo 'Tables Overview:'
\echo '════════════════════════════════════════════════════════════'
SELECT 
    t.tablename as "Table Name",
    COALESCE(td.description, '') as "Description",
    pg_size_pretty(pg_total_relation_size(t.schemaname||'.'||t.tablename)) AS "Size",
    COALESCE(s.n_live_tup, 0) as "Estimated Rows",
    COALESCE(s.n_dead_tup, 0) as "Dead Rows",
    CASE 
        WHEN s.n_live_tup > 0 
        THEN round((s.n_dead_tup::numeric / s.n_live_tup::numeric) * 100, 2)
        ELSE 0
    END as "Bloat %"
FROM pg_tables t
LEFT JOIN pg_stat_user_tables s ON s.relname = t.tablename
LEFT JOIN pg_class c ON c.relname = t.tablename
LEFT JOIN pg_description td ON td.objoid = c.oid AND td.objsubid = 0
WHERE t.schemaname = 'public'
ORDER BY pg_total_relation_size(t.schemaname||'.'||t.tablename) DESC;

-- Connection Stats
\echo
\echo 'Connection Statistics:'
\echo '════════════════════════════════════════════════════════════'
SELECT 
    count(*) as "Total Connections",
    count(*) FILTER (WHERE state = 'active') as "Active",
    count(*) FILTER (WHERE state = 'idle') as "Idle",
    count(*) FILTER (WHERE state = 'idle in transaction') as "Idle in Transaction"
FROM pg_stat_activity
WHERE datname = current_database();
EOF
    
    echo
    read -p "Press Enter to continue..."
}

run_custom_query() {
    local host=$1
    local port=$2
    local user=$3
    local pass=$4
    local db=$5
    
    clear
    print_header
    print_section "Run Custom Query"
    
    echo -e "${BOLD}Enter your SQL query (end with ';'):${NC}"
    echo -e "${YELLOW}Tip: Use \\q to cancel${NC}"
    echo
    
    local query=""
    while IFS= read -r line; do
        [[ "$line" == '\q' ]] && return
        query+="$line"$'\n'
        [[ "$line" =~ \;$ ]] && break
    done
    
    echo
    print_info "Executing query..."
    echo
    
    PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" -c "$query" 2>&1 | less
    
    echo
    read -p "Press Enter to continue..."
}

export_table_data() {
    local host=$1
    local port=$2
    local user=$3
    local pass=$4
    local db=$5
    
    # Get list of tables
    local tables=($(get_table_list "$host" "$port" "$user" "$pass" "$db"))
    
    if [ ${#tables[@]} -eq 0 ]; then
        print_error "No tables found"
        read -p "Press Enter to continue..."
        return
    fi
    
    # Prepare menu
    local menu_options=()
    for table in "${tables[@]}"; do
        menu_options+=("Export $table to CSV")
    done
    menu_options+=("← Cancel")
    
    draw_menu "${menu_options[@]}"
    local choice=$?
    
    if [ $choice -eq 255 ] || [ $choice -eq ${#tables[@]} ]; then
        return
    fi
    
    local table=${tables[$choice]}
    local filename="${table}_$(date +%Y%m%d_%H%M%S).csv"
    
    clear
    print_header
    print_section "Exporting $table"
    
    print_info "Exporting to: $SCRIPT_DIR/$filename"
    
    PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" -c \
        "\COPY $table TO '$SCRIPT_DIR/$filename' WITH CSV HEADER"
    
    if [ $? -eq 0 ]; then
        print_success "Export completed successfully!"
        ls -lh "$SCRIPT_DIR/$filename"
    else
        print_error "Export failed"
    fi
    
    echo
    read -p "Press Enter to continue..."
}

# =====================================================
# Import existing functions from original script
# =====================================================

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

check_postgresql_installed() {
    if check_command psql && check_command postgres; then
        return 0
    else
        return 1
    fi
}

check_postgresql_running() {
    if sudo systemctl is-active --quiet postgresql; then
        return 0
    else
        return 1
    fi
}

test_db_connection() {
    local host=$1
    local port=$2
    local user=$3
    local pass=$4
    local db=$5
    
    PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" -c "SELECT 1;" &>/dev/null
}

confirm() {
    local prompt="$1"
    local default="${2:-n}"
    local response
    
    if [[ "$default" == "y" ]]; then
        prompt="$prompt [Y/n]: "
    else
        prompt="$prompt [y/N]: "
    fi
    
    read -p "$prompt" response
    response=${response:-$default}
    
    [[ "$response" =~ ^[Yy]$ ]]
}

# =====================================================
# Main Menu with Navigation
# =====================================================

show_main_menu_enhanced() {
    local options=(
        "🚀 Complete Setup (Interactive)"
        "⚡ Quick Setup (Default values)"
        "🔍 Test Database Connection"
        "📊 Database Status"
        "🔄 Migrate SQLite Data"
        "🛠️  Create Helper Scripts"
        "📚 View Documentation"
        "❌ Exit"
    )
    
    while true; do
        draw_menu "${options[@]}"
        local choice=$?
        
        # Handle quit
        if [ $choice -eq 255 ]; then
            print_info "Exiting..."
            exit 0
        fi
        
        case $choice in
            0)  # Complete Setup
                run_complete_setup
                ;;
            1)  # Quick Setup
                run_quick_setup
                ;;
            2)  # Test Connection (Enhanced)
                test_connection_enhanced
                ;;
            3)  # Database Status
                check_status_enhanced
                ;;
            4)  # Migrate Data
                migrate_from_sqlite
                ;;
            5)  # Create Helper Scripts
                create_helper_scripts_enhanced
                print_success "Helper scripts created"
                read -p "Press Enter to continue..."
                ;;
            6)  # View Documentation
                view_documentation
                ;;
            7)  # Exit
                print_info "Exiting..."
                exit 0
                ;;
        esac
    done
}

check_status_enhanced() {
    clear
    print_header
    print_section "PostgreSQL Status"
    
    if check_postgresql_installed; then
        print_success "PostgreSQL is installed"
        
        # Get version
        local pg_version=$(psql --version | awk '{print $3}')
        print_info "Version: $pg_version"
        
        if check_postgresql_running; then
            print_success "PostgreSQL service is active"
            
            # Show service details
            echo
            echo -e "${BOLD}Service Status:${NC}"
            sudo systemctl status postgresql --no-pager | head -n 15
            
            # Test connection
            source ~/.bashrc 2>/dev/null || true
            local host="${AUTOTRAINX_DB_HOST:-localhost}"
            local port="${AUTOTRAINX_DB_PORT:-5432}"
            local user="${AUTOTRAINX_DB_USER:-autotrainx}"
            local pass="${AUTOTRAINX_DB_PASSWORD:-1234}"
            local db="${AUTOTRAINX_DB_NAME:-autotrainx}"
            
            echo
            if test_db_connection "$host" "$port" "$user" "$pass" "$db"; then
                print_success "Database connection successful"
                
                # Show quick stats
                echo
                echo -e "${BOLD}Quick Statistics:${NC}"
                PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" -t << EOF
SELECT 
    'Database Size: ' || pg_size_pretty(pg_database_size('$db'));
SELECT 
    'Total Tables: ' || COUNT(*) FROM pg_tables WHERE schemaname = 'public';
SELECT 
    'Total Records (executions): ' || COUNT(*) FROM executions;
EOF
            else
                print_error "Cannot connect to database"
            fi
        else
            print_error "PostgreSQL service is not running"
            if confirm "Start PostgreSQL service?" "y"; then
                sudo systemctl start postgresql
                print_success "PostgreSQL service started"
            fi
        fi
    else
        print_error "PostgreSQL is not installed"
    fi
    
    echo
    read -p "Press Enter to continue..."
}

view_documentation() {
    clear
    print_header
    print_section "PostgreSQL Setup Documentation"
    
    echo -e "${BOLD}Quick Reference:${NC}"
    echo
    echo "1. ${BOLD}Environment Variables:${NC}"
    echo "   AUTOTRAINX_DB_TYPE=postgresql"
    echo "   AUTOTRAINX_DB_HOST=localhost"
    echo "   AUTOTRAINX_DB_PORT=5432"
    echo "   AUTOTRAINX_DB_NAME=autotrainx"
    echo "   AUTOTRAINX_DB_USER=autotrainx"
    echo "   AUTOTRAINX_DB_PASSWORD=1234"
    echo
    echo "2. ${BOLD}Common Commands:${NC}"
    echo "   Connect to DB:     psql -h localhost -U autotrainx -d autotrainx"
    echo "   List tables:       \\dt"
    echo "   Describe table:    \\d tablename"
    echo "   Exit psql:         \\q"
    echo
    echo "3. ${BOLD}Helper Scripts:${NC}"
    echo "   ./database_utils/pg_connect.sh    - Quick database connection"
    echo "   ./database_utils/pg_status.sh     - Database status and statistics"
    echo "   ./database_utils/pg_backup.sh     - Backup database to SQL file"
    echo
    echo "4. ${BOLD}Starting AutoTrainX:${NC}"
    echo "   API Server:        ./start_api_postgresql.sh"
    echo "   Main Program:      python main.py"
    echo
    read -p "Press Enter to continue..."
}

create_helper_scripts_enhanced() {
    print_step "Creating enhanced helper scripts..."
    
    # Enhanced connection script with menu
    cat > "$SCRIPT_DIR/pg_connect.sh" << 'EOF'
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
EOF
    chmod +x "$SCRIPT_DIR/pg_connect.sh"
    
    # Keep existing pg_status.sh and pg_backup.sh from original
    # ... (copy from original script)
    
    # New script: Table browser
    cat > "$SCRIPT_DIR/pg_browse.sh" << 'EOF'
#!/bin/bash
# Interactive PostgreSQL table browser
exec bash "$(dirname "$0")/setup_postgresql_interactive.sh" --browse
EOF
    chmod +x "$SCRIPT_DIR/pg_browse.sh"
    
    print_success "Enhanced helper scripts created"
}

# =====================================================
# Import remaining functions from original script
# =====================================================

install_postgresql() {
    print_section "PostgreSQL Installation"
    
    if check_postgresql_installed; then
        print_success "PostgreSQL is already installed"
        
        # Check version
        local pg_version=$(psql --version | awk '{print $3}')
        print_info "PostgreSQL version: $pg_version"
        
        if ! confirm "Do you want to continue with the existing installation?"; then
            print_warning "Aborting installation"
            return 1
        fi
    else
        print_info "PostgreSQL is not installed"
        
        if confirm "Do you want to install PostgreSQL now?" "y"; then
            print_step "Updating package list..."
            sudo apt update
            
            print_step "Installing PostgreSQL and contrib package..."
            sudo apt install -y postgresql postgresql-contrib
            
            if check_postgresql_installed; then
                print_success "PostgreSQL installed successfully"
            else
                print_error "Failed to install PostgreSQL"
                return 1
            fi
        else
            print_error "PostgreSQL installation is required to continue"
            return 1
        fi
    fi
    
    # Ensure PostgreSQL is running
    if ! check_postgresql_running; then
        print_step "Starting PostgreSQL service..."
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
    fi
    
    print_success "PostgreSQL service is running"
    return 0
}

configure_postgresql() {
    print_section "PostgreSQL Configuration"
    
    # Get database configuration from user
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
    
    if ! confirm "Proceed with this configuration?" "y"; then
        print_warning "Configuration cancelled"
        return 1
    fi
    
    # Create user and database
    print_step "Creating database and user..."
    
    sudo -u postgres psql <<EOF
-- Create user if not exists
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
GRANT ALL PRIVILEGES ON DATABASE $db_name TO $db_user;
EOF
    
    if [ $? -eq 0 ]; then
        print_success "Database and user created successfully"
    else
        print_error "Failed to create database and user"
        return 1
    fi
    
    # Test connection
    print_step "Testing database connection..."
    if test_db_connection "$db_host" "$db_port" "$db_user" "$db_password" "$db_name"; then
        print_success "Database connection successful"
    else
        print_error "Failed to connect to database"
        print_info "Checking pg_hba.conf configuration..."
        
        # Try to fix pg_hba.conf
        if confirm "Do you want to update pg_hba.conf for password authentication?" "y"; then
            update_pg_hba_conf
        fi
        return 1
    fi
    
    # Save configuration
    save_configuration "$db_name" "$db_user" "$db_password" "$db_host" "$db_port"
    
    return 0
}

update_pg_hba_conf() {
    print_step "Updating pg_hba.conf..."
    
    # Find pg_hba.conf
    local pg_version=$(sudo -u postgres psql -t -c "SHOW server_version;" | awk -F. '{print $1}')
    local pg_hba_conf="/etc/postgresql/$pg_version/main/pg_hba.conf"
    
    if [ ! -f "$pg_hba_conf" ]; then
        # Try to find it
        pg_hba_conf=$(sudo -u postgres psql -t -c "SHOW hba_file;" | xargs)
    fi
    
    if [ -f "$pg_hba_conf" ]; then
        print_info "Found pg_hba.conf at: $pg_hba_conf"
        
        # Backup original
        sudo cp "$pg_hba_conf" "$pg_hba_conf.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Update local connections to use md5
        sudo sed -i 's/local   all             all                                     peer/local   all             all                                     md5/g' "$pg_hba_conf"
        
        # Restart PostgreSQL
        print_step "Restarting PostgreSQL..."
        sudo systemctl restart postgresql
        
        print_success "pg_hba.conf updated successfully"
    else
        print_error "Could not find pg_hba.conf"
    fi
}

save_configuration() {
    local db_name=$1
    local db_user=$2
    local db_password=$3
    local db_host=$4
    local db_port=$5
    
    print_section "Save Configuration"
    
    echo -e "${BOLD}Choose how to save the configuration:${NC}"
    echo "1) Environment variables (add to ~/.bashrc)"
    echo "2) Create .env file"
    echo "3) Both"
    echo "4) Skip"
    echo
    
    read -p "Your choice [1-4]: " choice
    
    case $choice in
        1|3)
            print_step "Adding to ~/.bashrc..."
            
            # Backup .bashrc
            cp ~/.bashrc ~/.bashrc.backup.$(date +%Y%m%d_%H%M%S)
            
            # Add configuration
            cat >> ~/.bashrc << EOF

# AutoTrainX PostgreSQL Configuration
export AUTOTRAINX_DB_TYPE=postgresql
export AUTOTRAINX_DB_HOST=$db_host
export AUTOTRAINX_DB_PORT=$db_port
export AUTOTRAINX_DB_NAME=$db_name
export AUTOTRAINX_DB_USER=$db_user
export AUTOTRAINX_DB_PASSWORD=$db_password
EOF
            
            print_success "Configuration added to ~/.bashrc"
            print_info "Run 'source ~/.bashrc' to apply changes"
            ;;&
            
        2|3)
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
            ;;
            
        4)
            print_info "Skipping configuration save"
            ;;
            
        *)
            print_error "Invalid choice"
            ;;
    esac
}

migrate_from_sqlite() {
    print_section "SQLite to PostgreSQL Migration"
    
    local sqlite_db="$SCRIPT_DIR/DB/executions.db"
    
    if [ ! -f "$sqlite_db" ]; then
        print_warning "No SQLite database found at $sqlite_db"
        print_info "Skipping migration"
        return 0
    fi
    
    # Show SQLite database info
    print_info "Found SQLite database:"
    ls -lh "$sqlite_db"
    
    # Count records
    local record_count=$(sqlite3 "$sqlite_db" "SELECT COUNT(*) FROM executions;" 2>/dev/null || echo "0")
    print_info "Records in SQLite database: $record_count"
    
    if [ "$record_count" -eq 0 ]; then
        print_info "No records to migrate"
        return 0
    fi
    
    if confirm "Do you want to migrate data from SQLite to PostgreSQL?" "y"; then
        print_step "Starting migration..."
        
        # Check if migration script exists
        if [ -f "$SCRIPT_DIR/migrate_simple.py" ]; then
            python "$SCRIPT_DIR/migrate_simple.py"
            
            if [ $? -eq 0 ]; then
                print_success "Migration completed successfully"
                
                # Verify migration
                if [ -f "$SCRIPT_DIR/verify_postgresql.py" ]; then
                    print_step "Verifying migration..."
                    python "$SCRIPT_DIR/verify_postgresql.py"
                fi
            else
                print_error "Migration failed"
                return 1
            fi
        else
            print_error "Migration script not found"
            return 1
        fi
    else
        print_info "Skipping migration"
    fi
    
    return 0
}

run_complete_setup() {
    clear
    print_header
    
    print_info "This script will help you setup PostgreSQL for AutoTrainX"
    print_info "Current directory: $SCRIPT_DIR"
    echo
    
    if ! confirm "Do you want to continue?" "y"; then
        print_warning "Setup cancelled"
        return
    fi
    
    # Step 1: Install PostgreSQL
    if ! install_postgresql; then
        print_error "Failed to install PostgreSQL"
        read -p "Press Enter to continue..."
        return
    fi
    
    # Step 2: Configure PostgreSQL
    if ! configure_postgresql; then
        print_error "Failed to configure PostgreSQL"
        read -p "Press Enter to continue..."
        return
    fi
    
    # Step 3: Migrate data
    migrate_from_sqlite
    
    # Step 4: Create helper scripts
    create_helper_scripts_enhanced
    
    # Final summary
    print_section "Setup Complete!"
    
    print_success "PostgreSQL has been configured for AutoTrainX"
    echo
    print_info "Next steps:"
    echo "1. Run: source ~/.bashrc"
    echo "2. Test connection: ./database_utils/pg_connect.sh"
    echo "3. Check status: ./database_utils/pg_status.sh"
    echo "4. Start AutoTrainX with PostgreSQL:"
    echo "   - API: ./start_api_postgresql.sh"
    echo "   - Main: python main.py"
    echo
    
    read -p "Press Enter to continue..."
}

run_quick_setup() {
    clear
    print_header
    print_section "Quick Setup (Default Values)"
    
    print_info "Using default configuration:"
    echo "  Database: $DEFAULT_DB_NAME"
    echo "  User: $DEFAULT_DB_USER"
    echo "  Password: $DEFAULT_DB_PASSWORD"
    echo "  Host: $DEFAULT_DB_HOST"
    echo "  Port: $DEFAULT_DB_PORT"
    echo
    
    if ! confirm "Proceed with quick setup?" "y"; then
        print_info "Switching to interactive setup..."
        run_complete_setup
        return
    fi
    
    # Install PostgreSQL
    if ! install_postgresql; then
        read -p "Press Enter to continue..."
        return
    fi
    
    # Create database with defaults
    print_step "Creating database with default values..."
    sudo -u postgres psql <<EOF
CREATE USER $DEFAULT_DB_USER WITH PASSWORD '$DEFAULT_DB_PASSWORD';
CREATE DATABASE $DEFAULT_DB_NAME OWNER $DEFAULT_DB_USER;
GRANT ALL PRIVILEGES ON DATABASE $DEFAULT_DB_NAME TO $DEFAULT_DB_USER;
EOF
    
    # Save configuration
    save_configuration "$DEFAULT_DB_NAME" "$DEFAULT_DB_USER" "$DEFAULT_DB_PASSWORD" \
                      "$DEFAULT_DB_HOST" "$DEFAULT_DB_PORT"
    
    # Migrate data
    migrate_from_sqlite
    
    print_success "Quick setup complete!"
    read -p "Press Enter to continue..."
}

# =====================================================
# Script Entry Point
# =====================================================

# Check if running with arguments
if [ $# -gt 0 ]; then
    case "$1" in
        --quick|-q)
            run_quick_setup
            ;;
        --browse|-b)
            source ~/.bashrc 2>/dev/null || true
            test_connection_enhanced
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --quick, -q     Run quick setup with default values"
            echo "  --browse, -b    Browse database tables interactively"
            echo "  --help, -h      Show this help message"
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
else
    # Interactive menu with navigation
    show_main_menu_enhanced
fi
#!/bin/bash
# Quick PostgreSQL Setup for AutoTrainX

echo "========================================"
echo "  PostgreSQL Quick Setup for AutoTrainX"
echo "========================================"
echo ""
echo "This script will:"
echo "1. Install PostgreSQL (if needed)"
echo "2. Create database and user"
echo "3. Configure authentication"
echo "4. Run initial setup"
echo ""

# Check if running as root
RUNNING_AS_ROOT=false
if [ "$EUID" -eq 0 ]; then 
   echo "⚠️  Warning: Running as root. Proceeding with caution..."
   RUNNING_AS_ROOT=true
fi

# Run commands with appropriate privileges
run_privileged() {
    if [ "$RUNNING_AS_ROOT" = true ]; then
        # When running as root, use su for postgres user operations
        if [ "$1" = "-u" ] && [ "$2" = "postgres" ]; then
            shift 2  # Remove -u postgres from arguments
            su - postgres -c "$*"
        else
            "$@"
        fi
    else
        sudo "$@"
    fi
}

# Function to check if PostgreSQL is installed
check_postgresql() {
    if command -v psql &> /dev/null; then
        echo "✅ PostgreSQL is already installed"
        return 0
    else
        echo "❌ PostgreSQL is not installed"
        return 1
    fi
}

# Function to start PostgreSQL service
start_postgresql() {
    echo "🔄 Starting PostgreSQL service..."
    
    # Check if already running
    if su - postgres -c "pg_isready" &> /dev/null 2>&1; then
        echo "✅ PostgreSQL is already running"
        return 0
    fi
    
    # Try direct pg_ctl first (works better in containers)
    if su - postgres -c "pg_ctl status -D /var/lib/postgresql/*/main" &> /dev/null; then
        DATA_DIR=$(su - postgres -c "find /var/lib/postgresql -name 'main' -type d 2>/dev/null | head -1")
        if [ -n "$DATA_DIR" ]; then
            echo "📁 Using data directory: $DATA_DIR"
            su - postgres -c "pg_ctl -D '$DATA_DIR' -l '$DATA_DIR/postgresql.log' start" &> /dev/null
            sleep 3
        fi
    fi
    
    # If that didn't work, try service command
    if ! su - postgres -c "pg_isready" &> /dev/null 2>&1; then
        if command -v service &> /dev/null; then
            echo "🔧 Trying service command..."
            service postgresql start &> /dev/null
            sleep 3
        fi
    fi
    
    # If still not working, try manual start
    if ! su - postgres -c "pg_isready" &> /dev/null 2>&1; then
        echo "🔧 Attempting manual PostgreSQL start..."
        # Create run directory if needed
        mkdir -p /var/run/postgresql
        chown postgres:postgres /var/run/postgresql
        
        # Find PostgreSQL version and data directory
        PG_VERSION=$(ls /etc/postgresql/ 2>/dev/null | head -1)
        if [ -n "$PG_VERSION" ]; then
            DATA_DIR="/var/lib/postgresql/$PG_VERSION/main"
            CONFIG_DIR="/etc/postgresql/$PG_VERSION/main"
            
            if [ -d "$DATA_DIR" ]; then
                echo "📁 Using PostgreSQL $PG_VERSION data directory: $DATA_DIR"
                su - postgres -c "/usr/lib/postgresql/$PG_VERSION/bin/postgres -D '$DATA_DIR' -c 'config_file=$CONFIG_DIR/postgresql.conf'" &
                sleep 3
            fi
        fi
    fi
    
    # Final check
    if su - postgres -c "pg_isready" &> /dev/null 2>&1; then
        echo "✅ PostgreSQL is running"
        return 0
    else
        echo "❌ PostgreSQL failed to start"
        echo "💡 You may need to initialize the database first with: su - postgres -c 'initdb -D /var/lib/postgresql/data'"
        return 1
    fi
}

# Install PostgreSQL
install_postgresql() {
    echo ""
    echo "Installing PostgreSQL..."
    run_privileged apt-get update
    run_privileged apt-get install -y postgresql postgresql-client postgresql-contrib
    
    if [ $? -eq 0 ]; then
        echo "✅ PostgreSQL installed successfully"
    else
        echo "❌ Failed to install PostgreSQL"
        exit 1
    fi
}

# Create database and user
setup_database() {
    echo ""
    echo "Creating database and user..."
    
    # Get password from environment or prompt
    if [ -z "$DATABASE_PASSWORD" ]; then
        echo "Enter password for PostgreSQL user 'autotrainx':"
        read -s DATABASE_PASSWORD
        if [ -z "$DATABASE_PASSWORD" ]; then
            echo "❌ Password cannot be empty"
            exit 1
        fi
    fi
    
    echo "Using password from environment variable or user input..."
    
    # Create SQL commands
    run_privileged -u postgres psql <<EOF
-- Create user
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'autotrainx') THEN
      CREATE USER autotrainx WITH PASSWORD '$DATABASE_PASSWORD';
   END IF;
END \$\$;

-- Create database
SELECT 'CREATE DATABASE autotrainx OWNER autotrainx'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'autotrainx')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE autotrainx TO autotrainx;

-- Show result
\l autotrainx
\du autotrainx
EOF

    if [ $? -eq 0 ]; then
        echo "✅ Database and user created successfully"
    else
        echo "❌ Failed to create database/user"
        exit 1
    fi
}

# Fix authentication
fix_authentication() {
    echo ""
    echo "Configuring authentication..."
    
    # Find pg_hba.conf
    PG_VERSION=$(run_privileged -u postgres psql -t -c "SELECT version();" | grep -oP '\d+(?=\.)')
    HBA_FILE="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
    
    if [ -f "$HBA_FILE" ]; then
        # Backup original
        run_privileged cp "$HBA_FILE" "$HBA_FILE.backup"
        
        # Update authentication method
        run_privileged sed -i 's/local   all             postgres                                peer/local   all             postgres                                md5/' "$HBA_FILE"
        run_privileged sed -i 's/local   all             all                                     peer/local   all             all                                     md5/' "$HBA_FILE"
        
        # Restart PostgreSQL
        run_privileged systemctl restart postgresql
        
        echo "✅ Authentication configured"
    else
        echo "⚠️  Could not find pg_hba.conf - manual configuration may be needed"
    fi
}

# Test connection
test_connection() {
    echo ""
    echo "Testing connection..."
    
    PGPASSWORD=1234 psql -h localhost -U autotrainx -d autotrainx -c "SELECT version();" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✅ Connection test successful!"
        return 0
    else
        echo "❌ Connection test failed"
        return 1
    fi
}

# Main execution
echo "Starting setup..."

# Check if PostgreSQL is installed
if ! check_postgresql; then
    read -p "Install PostgreSQL? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_postgresql
    else
        echo "PostgreSQL is required. Exiting."
        exit 1
    fi
fi

# Start PostgreSQL service
if ! start_postgresql; then
    echo "❌ Failed to start PostgreSQL service"
    exit 1
fi

# Setup database
setup_database

# Fix authentication
fix_authentication

# Test connection
if test_connection; then
    echo ""
    echo "========================================"
    echo "✅ PostgreSQL setup completed!"
    echo ""
    echo "Connection details:"
    echo "  Host: localhost"
    echo "  Port: 5432"
    echo "  Database: autotrainx"
    echo "  User: autotrainx"
    echo "  Password: 1234"
    echo ""
    echo "You can now:"
    echo "1. Run: python postgresql_manager.py"
    echo "2. Connect: psql -h localhost -U autotrainx -d autotrainx"
    echo "========================================"
else
    echo ""
    echo "⚠️  Setup completed but connection test failed"
    echo "You may need to check the authentication settings"
    echo ""
    echo "Try running: python postgresql_manager.py"
    echo "And use the 'Fix Authentication Issues' option"
fi
#!/bin/bash
# AutoTrainX PostgreSQL Setup Script
# This script automates the installation and configuration of PostgreSQL for AutoTrainX

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DB_NAME="autotrainx"
DB_USER="autotrainx"
DB_PASSWORD="1234"

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   AutoTrainX PostgreSQL Setup Script${NC}"
echo -e "${GREEN}================================================${NC}"
echo

# Function to check if PostgreSQL is installed
check_postgresql() {
    if command -v psql &> /dev/null; then
        echo -e "${GREEN}✓ PostgreSQL is already installed${NC}"
        return 0
    else
        echo -e "${YELLOW}PostgreSQL is not installed${NC}"
        return 1
    fi
}

# Function to install PostgreSQL
install_postgresql() {
    echo -e "${YELLOW}Installing PostgreSQL...${NC}"
    sudo apt update
    sudo apt install -y postgresql postgresql-contrib
    echo -e "${GREEN}✓ PostgreSQL installed successfully${NC}"
}

# Function to start PostgreSQL service
start_postgresql() {
    echo -e "${YELLOW}Starting PostgreSQL service...${NC}"
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
    echo -e "${GREEN}✓ PostgreSQL service started and enabled${NC}"
}

# Function to create database and user
setup_database() {
    echo -e "${YELLOW}Setting up database and user...${NC}"
    
    # Check if user exists
    USER_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_user WHERE usename='$DB_USER'")
    
    if [ "$USER_EXISTS" = "1" ]; then
        echo -e "${YELLOW}User $DB_USER already exists${NC}"
        # Ask if user wants to reset password
        read -p "Do you want to reset the password? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo -u postgres psql << EOF
ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
EOF
            echo -e "${GREEN}✓ Password reset successfully${NC}"
        fi
    else
        # Create user
        sudo -u postgres psql << EOF
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
EOF
        echo -e "${GREEN}✓ User $DB_USER created${NC}"
    fi
    
    # Check if database exists
    DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")
    
    if [ "$DB_EXISTS" = "1" ]; then
        echo -e "${YELLOW}Database $DB_NAME already exists${NC}"
    else
        # Create database
        sudo -u postgres psql << EOF
CREATE DATABASE $DB_NAME OWNER $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF
        echo -e "${GREEN}✓ Database $DB_NAME created${NC}"
    fi
}

# Function to test connection
test_connection() {
    echo -e "${YELLOW}Testing connection...${NC}"
    
    if PGPASSWORD=$DB_PASSWORD psql -h localhost -U $DB_USER -d $DB_NAME -c '\q' 2>/dev/null; then
        echo -e "${GREEN}✓ Connection successful!${NC}"
        return 0
    else
        echo -e "${RED}✗ Connection failed${NC}"
        return 1
    fi
}

# Function to configure AutoTrainX
configure_autotrainx() {
    echo
    echo -e "${YELLOW}Configure AutoTrainX to use PostgreSQL?${NC}"
    echo "This will add environment variables to your ~/.bashrc"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Backup .bashrc
        cp ~/.bashrc ~/.bashrc.backup_$(date +%Y%m%d_%H%M%S)
        
        # Check if already configured
        if grep -q "AUTOTRAINX_DB_TYPE=postgresql" ~/.bashrc; then
            echo -e "${YELLOW}AutoTrainX PostgreSQL configuration already exists in .bashrc${NC}"
        else
            # Add configuration
            cat >> ~/.bashrc << EOF

# AutoTrainX PostgreSQL Configuration
export AUTOTRAINX_DB_TYPE=postgresql
export AUTOTRAINX_DB_HOST=localhost
export AUTOTRAINX_DB_PORT=5432
export AUTOTRAINX_DB_NAME=$DB_NAME
export AUTOTRAINX_DB_USER=$DB_USER
export AUTOTRAINX_DB_PASSWORD=$DB_PASSWORD
EOF
            echo -e "${GREEN}✓ Configuration added to ~/.bashrc${NC}"
            echo -e "${YELLOW}Run 'source ~/.bashrc' to apply changes${NC}"
        fi
    fi
}

# Function to show next steps
show_next_steps() {
    echo
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}   Setup Complete!${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Apply environment variables:"
    echo "   ${GREEN}source ~/.bashrc${NC}"
    echo
    echo "2. Migrate existing data (if any):"
    echo "   ${GREEN}python database_utils/migrate_simple.py${NC}"
    echo
    echo "3. Verify installation:"
    echo "   ${GREEN}python database_utils/verify_postgresql.py${NC}"
    echo
    echo "4. Configure VSCode SQLTools:"
    echo "   - Server: localhost"
    echo "   - Port: 5432"
    echo "   - Database: $DB_NAME"
    echo "   - Username: $DB_USER"
    echo "   - Password: $DB_PASSWORD"
    echo
    echo -e "${GREEN}Database connection details saved in this script${NC}"
}

# Main execution
main() {
    echo "This script will install and configure PostgreSQL for AutoTrainX"
    echo "Database: $DB_NAME"
    echo "User: $DB_USER"
    echo "Password: $DB_PASSWORD"
    echo
    read -p "Continue with installation? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled"
        exit 1
    fi
    
    # Check and install PostgreSQL
    if ! check_postgresql; then
        install_postgresql
    fi
    
    # Start service
    start_postgresql
    
    # Setup database
    setup_database
    
    # Test connection
    if test_connection; then
        # Ask about AutoTrainX configuration
        configure_autotrainx
        
        # Show next steps
        show_next_steps
    else
        echo -e "${RED}There was an error setting up the database${NC}"
        echo "Please check the PostgreSQL logs:"
        echo "  sudo journalctl -u postgresql -n 50"
        exit 1
    fi
}

# Run main function
main
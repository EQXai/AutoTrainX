#!/bin/bash

# =====================================================
# PostgreSQL Setup Verification Script
# =====================================================
# This script verifies that PostgreSQL is properly
# configured for AutoTrainX
# =====================================================

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# =====================================================
# Helper Functions
# =====================================================

print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_header() {
    echo -e "\n${BOLD}=== $1 ===${NC}\n"
}

# =====================================================
# Test Functions
# =====================================================

test_postgresql_installed() {
    print_header "PostgreSQL Installation"
    
    print_test "Checking if PostgreSQL is installed..."
    if command -v psql &> /dev/null && command -v postgres &> /dev/null; then
        local version=$(psql --version | awk '{print $3}')
        print_pass "PostgreSQL is installed (version: $version)"
        return 0
    else
        print_fail "PostgreSQL is not installed"
        return 1
    fi
}

test_postgresql_service() {
    print_header "PostgreSQL Service"
    
    print_test "Checking if PostgreSQL service is running..."
    if sudo systemctl is-active --quiet postgresql; then
        print_pass "PostgreSQL service is active"
        
        # Check if enabled at boot
        if sudo systemctl is-enabled --quiet postgresql; then
            print_pass "PostgreSQL is enabled at system startup"
        else
            print_fail "PostgreSQL is not enabled at system startup"
        fi
        return 0
    else
        print_fail "PostgreSQL service is not running"
        return 1
    fi
}

test_environment_variables() {
    print_header "Environment Variables"
    
    # Source bashrc to get latest variables
    source ~/.bashrc 2>/dev/null || true
    
    local required_vars=(
        "AUTOTRAINX_DB_TYPE"
        "AUTOTRAINX_DB_HOST"
        "AUTOTRAINX_DB_PORT"
        "AUTOTRAINX_DB_NAME"
        "AUTOTRAINX_DB_USER"
        "AUTOTRAINX_DB_PASSWORD"
    )
    
    local all_set=true
    for var in "${required_vars[@]}"; do
        print_test "Checking $var..."
        if [ -n "${!var}" ]; then
            if [ "$var" != "AUTOTRAINX_DB_PASSWORD" ]; then
                print_pass "$var is set: ${!var}"
            else
                print_pass "$var is set: ****"
            fi
        else
            print_fail "$var is not set"
            all_set=false
        fi
    done
    
    # Check if DB_TYPE is postgresql
    if [ "$AUTOTRAINX_DB_TYPE" = "postgresql" ]; then
        print_pass "Database type is correctly set to PostgreSQL"
    else
        print_fail "Database type is not set to PostgreSQL (current: $AUTOTRAINX_DB_TYPE)"
        all_set=false
    fi
    
    return $([ "$all_set" = true ] && echo 0 || echo 1)
}

test_database_connection() {
    print_header "Database Connection"
    
    source ~/.bashrc 2>/dev/null || true
    
    local host=${AUTOTRAINX_DB_HOST:-localhost}
    local port=${AUTOTRAINX_DB_PORT:-5432}
    local user=${AUTOTRAINX_DB_USER:-autotrainx}
    local pass=${AUTOTRAINX_DB_PASSWORD:-1234}
    local db=${AUTOTRAINX_DB_NAME:-autotrainx}
    
    print_test "Testing database connection..."
    if PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" -c "SELECT 1;" &>/dev/null; then
        print_pass "Successfully connected to database"
        
        # Check if tables exist
        print_test "Checking if tables exist..."
        local tables=$(PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
        tables=$(echo $tables | xargs)
        
        if [ "$tables" -gt 0 ]; then
            print_pass "Found $tables tables in database"
            
            # Check specific tables
            for table in "executions" "variations"; do
                if PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" -t -c "SELECT 1 FROM $table LIMIT 1;" &>/dev/null; then
                    local count=$(PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" -t -c "SELECT COUNT(*) FROM $table;")
                    count=$(echo $count | xargs)
                    print_pass "Table '$table' exists with $count records"
                else
                    print_fail "Table '$table' does not exist or is empty"
                fi
            done
        else
            print_fail "No tables found in database"
        fi
        
        return 0
    else
        print_fail "Cannot connect to database"
        return 1
    fi
}

test_python_connection() {
    print_header "Python Database Connection"
    
    print_test "Testing Python psycopg2 connection..."
    
    # Create temporary Python script
    cat > /tmp/test_pg_connection.py << 'EOF'
import os
import sys
try:
    import psycopg2
    
    # Get connection parameters from environment
    conn_params = {
        "host": os.getenv("AUTOTRAINX_DB_HOST", "localhost"),
        "port": os.getenv("AUTOTRAINX_DB_PORT", "5432"),
        "database": os.getenv("AUTOTRAINX_DB_NAME", "autotrainx"),
        "user": os.getenv("AUTOTRAINX_DB_USER", "autotrainx"),
        "password": os.getenv("AUTOTRAINX_DB_PASSWORD", "1234")
    }
    
    # Try to connect
    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print(f"SUCCESS: Connected to PostgreSQL")
    print(f"Version: {version}")
    cur.close()
    conn.close()
    sys.exit(0)
except ImportError:
    print("ERROR: psycopg2 not installed")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
EOF
    
    source ~/.bashrc 2>/dev/null || true
    output=$(python /tmp/test_pg_connection.py 2>&1)
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        print_pass "Python can connect to PostgreSQL"
        print_info "$output"
    else
        print_fail "Python connection failed"
        print_info "$output"
    fi
    
    rm -f /tmp/test_pg_connection.py
    return $exit_code
}

test_autotrainx_integration() {
    print_header "AutoTrainX Integration"
    
    # Check if main.py exists
    print_test "Checking AutoTrainX files..."
    if [ -f "main.py" ]; then
        print_pass "main.py found"
    else
        print_fail "main.py not found in current directory"
        return 1
    fi
    
    # Check if database manager supports PostgreSQL
    print_test "Checking database manager PostgreSQL support..."
    if grep -q "postgresql" src/database/factory.py 2>/dev/null; then
        print_pass "Database factory supports PostgreSQL"
    else
        print_fail "Database factory may not support PostgreSQL"
    fi
    
    # Check if API startup script exists
    if [ -f "start_api_postgresql.sh" ]; then
        print_pass "PostgreSQL API startup script exists"
    else
        print_fail "PostgreSQL API startup script not found"
    fi
    
    return 0
}

test_helper_scripts() {
    print_header "Helper Scripts"
    
    local scripts=("database_utils/pg_connect.sh" "database_utils/pg_status.sh" "database_utils/pg_backup.sh")
    local all_found=true
    
    for script in "${scripts[@]}"; do
        print_test "Checking for $script..."
        if [ -f "$script" ] && [ -x "$script" ]; then
            print_pass "$script exists and is executable"
        else
            print_fail "$script not found or not executable"
            all_found=false
        fi
    done
    
    return $([ "$all_found" = true ] && echo 0 || echo 1)
}

# =====================================================
# Summary Function
# =====================================================

print_summary() {
    echo
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}           TEST SUMMARY                 ${NC}"
    echo -e "${BOLD}========================================${NC}"
    echo
    echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
    echo
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}${BOLD}✅ All tests passed! PostgreSQL is properly configured for AutoTrainX${NC}"
        echo
        echo "You can now:"
        echo "1. Start the API: ./start_api_postgresql.sh"
        echo "2. Run AutoTrainX: python main.py"
        echo "3. Connect to database: ./database_utils/pg_connect.sh"
    else
        echo -e "${RED}${BOLD}❌ Some tests failed. Please run the setup script again.${NC}"
        echo
        echo "To fix issues, run: ./database_utils/setup_postgresql_interactive.sh"
    fi
    echo
}

# =====================================================
# Main
# =====================================================

clear
echo -e "${BOLD}AutoTrainX PostgreSQL Setup Verification${NC}"
echo "========================================"
echo

# Run all tests
test_postgresql_installed
test_postgresql_service
test_environment_variables
test_database_connection
test_python_connection
test_autotrainx_integration
test_helper_scripts

# Print summary
print_summary

# Exit with appropriate code
exit $TESTS_FAILED
#!/usr/bin/env python3
"""Verify complete PostgreSQL integration across all components."""

import os
import sys
import time
import subprocess
import requests
import psycopg2
from pathlib import Path
import json

# Colors for output
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def print_section(title):
    """Print a section header."""
    print(f"\n{BLUE}{'=' * 60}{NC}")
    print(f"{BLUE}{title}{NC}")
    print(f"{BLUE}{'=' * 60}{NC}")

def check_environment():
    """Check environment variables."""
    print_section("1. Checking Environment Variables")
    
    required_vars = {
        'DATABASE_TYPE': 'postgresql',
        'AUTOTRAINX_DB_TYPE': 'postgresql',
        'AUTOTRAINX_DB_HOST': 'localhost',
        'AUTOTRAINX_DB_NAME': 'autotrainx',
        'AUTOTRAINX_DB_USER': 'autotrainx',
        'AUTOTRAINX_DB_PASSWORD': '1234'
    }
    
    all_good = True
    for var, expected in required_vars.items():
        value = os.environ.get(var)
        if value == expected:
            print(f"{GREEN}✅ {var} = {value}{NC}")
        else:
            print(f"{RED}❌ {var} = {value} (expected: {expected}){NC}")
            all_good = False
    
    return all_good

def check_sqlite_not_used():
    """Check that SQLite is not being used."""
    print_section("2. Checking SQLite is NOT in use")
    
    db_path = Path("DB/executions.db")
    
    # Check if file exists
    if db_path.exists():
        print(f"{YELLOW}⚠️  SQLite file exists: {db_path}{NC}")
        
        # Check if any process has it open
        try:
            result = subprocess.run(['lsof', str(db_path)], 
                                  capture_output=True, text=True)
            if result.stdout:
                print(f"{RED}❌ SQLite file is OPEN by processes:{NC}")
                print(result.stdout)
                return False
            else:
                print(f"{GREEN}✅ SQLite file exists but is NOT open{NC}")
        except:
            print(f"{YELLOW}⚠️  Could not check file locks{NC}")
    else:
        print(f"{GREEN}✅ SQLite file does not exist{NC}")
    
    return True

def check_api_running():
    """Check if API is running and using PostgreSQL."""
    print_section("3. Checking API Status")
    
    try:
        # Check health
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print(f"{GREEN}✅ API is running{NC}")
        else:
            print(f"{RED}❌ API returned status {response.status_code}{NC}")
            return False
            
        # Check database info
        response = requests.get("http://localhost:8000/api/v1/database/info", timeout=2)
        if response.status_code == 200:
            data = response.json()
            db_info = data.get('data', {})
            dialect = db_info.get('dialect', 'unknown')
            
            if dialect == 'postgresql':
                print(f"{GREEN}✅ API is using PostgreSQL{NC}")
                print(f"   URL: {db_info.get('url')}")
                print(f"   Tables: {db_info.get('table_count')}")
                return True
            else:
                print(f"{RED}❌ API is using {dialect} instead of PostgreSQL{NC}")
                return False
        else:
            print(f"{RED}❌ Could not get database info{NC}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"{RED}❌ API is not running on http://localhost:8000{NC}")
        return False
    except Exception as e:
        print(f"{RED}❌ Error checking API: {e}{NC}")
        return False

def check_postgresql_data():
    """Check PostgreSQL database directly."""
    print_section("4. Checking PostgreSQL Database")
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="autotrainx",
            user="autotrainx",
            password="1234"
        )
        cursor = conn.cursor()
        
        # Count executions
        cursor.execute("SELECT COUNT(*) FROM executions")
        count = cursor.fetchone()[0]
        print(f"{GREEN}✅ Connected to PostgreSQL{NC}")
        print(f"   Total executions: {count}")
        
        # Get latest execution
        cursor.execute("""
            SELECT job_id, dataset_name, status, created_at 
            FROM executions 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        latest = cursor.fetchone()
        if latest:
            print(f"   Latest job: {latest[0]}")
            print(f"   Dataset: {latest[1]}")
            print(f"   Status: {latest[2]}")
            print(f"   Created: {latest[3]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"{RED}❌ Could not connect to PostgreSQL: {e}{NC}")
        return False

def check_sheets_sync():
    """Check Google Sheets sync daemon status."""
    print_section("5. Checking Google Sheets Sync")
    
    try:
        # Check daemon status
        result = subprocess.run(['./manage_sheets_sync.sh', 'status'], 
                              capture_output=True, text=True)
        
        if "is running" in result.stdout:
            print(f"{GREEN}✅ Sheets sync daemon is running{NC}")
            
            # Check if using PostgreSQL
            if "postgresql" in result.stdout.lower():
                print(f"{GREEN}✅ Sheets sync is using PostgreSQL{NC}")
                return True
            else:
                print(f"{YELLOW}⚠️  Sheets sync might not be using PostgreSQL{NC}")
                return False
        else:
            print(f"{RED}❌ Sheets sync daemon is NOT running{NC}")
            print(result.stdout)
            return False
            
    except Exception as e:
        print(f"{RED}❌ Error checking sheets sync: {e}{NC}")
        return False

def create_test_job():
    """Create a test job via API."""
    print_section("6. Creating Test Job")
    
    try:
        # Create a unique job ID
        test_job_id = f"test_pg_{int(time.time())}"
        
        # Prepare job data
        job_data = {
            "dataset_name": "test_postgresql_integration",
            "preset_name": "TestPreset",
            "base_model": "test_model",
            "strategy": "single"
        }
        
        print(f"Creating job: {test_job_id}")
        
        # Send request
        response = requests.post(
            "http://localhost:8000/api/v1/jobs",
            json=job_data,
            timeout=5
        )
        
        if response.status_code in [200, 201]:
            print(f"{GREEN}✅ Job created successfully{NC}")
            job_response = response.json()
            
            if job_response.get('success'):
                job_id = job_response.get('data', {}).get('job', {}).get('id')
                print(f"   Job ID: {job_id}")
                return job_id
            else:
                print(f"{RED}❌ Job creation failed: {job_response.get('message')}{NC}")
                return None
        else:
            print(f"{RED}❌ Job creation failed with status {response.status_code}{NC}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"{RED}❌ Error creating job: {e}{NC}")
        return None

def verify_job_in_postgresql(job_id):
    """Verify the job exists in PostgreSQL."""
    print_section("7. Verifying Job in PostgreSQL")
    
    if not job_id:
        print(f"{YELLOW}⚠️  No job ID to verify{NC}")
        return False
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="autotrainx",
            user="autotrainx",
            password="1234"
        )
        cursor = conn.cursor()
        
        # Look for the job
        cursor.execute(
            "SELECT job_id, dataset_name, status FROM executions WHERE job_id = %s",
            (job_id,)
        )
        result = cursor.fetchone()
        
        if result:
            print(f"{GREEN}✅ Job found in PostgreSQL!{NC}")
            print(f"   Job ID: {result[0]}")
            print(f"   Dataset: {result[1]}")
            print(f"   Status: {result[2]}")
            conn.close()
            return True
        else:
            print(f"{RED}❌ Job NOT found in PostgreSQL{NC}")
            
            # Check if it's in SQLite instead
            sqlite_path = Path("DB/executions.db")
            if sqlite_path.exists():
                print(f"{YELLOW}⚠️  Checking SQLite...{NC}")
                import sqlite3
                sqlite_conn = sqlite3.connect(str(sqlite_path))
                sqlite_cursor = sqlite_conn.cursor()
                sqlite_cursor.execute(
                    "SELECT job_id FROM executions WHERE job_id = ?",
                    (job_id,)
                )
                if sqlite_cursor.fetchone():
                    print(f"{RED}❌ Job found in SQLite instead! System is still using SQLite!{NC}")
                sqlite_conn.close()
            
            conn.close()
            return False
            
    except Exception as e:
        print(f"{RED}❌ Error checking PostgreSQL: {e}{NC}")
        return False

def main():
    """Run all verification steps."""
    print(f"{GREEN}PostgreSQL Integration Verification{NC}")
    print(f"{GREEN}==================================={NC}")
    
    results = {
        "environment": check_environment(),
        "sqlite_not_used": check_sqlite_not_used(),
        "api_running": check_api_running(),
        "postgresql_data": check_postgresql_data(),
        "sheets_sync": check_sheets_sync()
    }
    
    # If API is running, test job creation
    if results["api_running"]:
        job_id = create_test_job()
        if job_id:
            time.sleep(2)  # Give it time to save
            results["job_in_postgresql"] = verify_job_in_postgresql(job_id)
        else:
            results["job_in_postgresql"] = False
    else:
        print(f"\n{YELLOW}⚠️  Skipping job creation test (API not running){NC}")
        results["job_in_postgresql"] = False
    
    # Summary
    print_section("Summary")
    
    all_passed = all(results.values())
    
    for test, passed in results.items():
        status = f"{GREEN}✅ PASS{NC}" if passed else f"{RED}❌ FAIL{NC}"
        print(f"{test}: {status}")
    
    if all_passed:
        print(f"\n{GREEN}🎉 All tests passed! PostgreSQL integration is working correctly!{NC}")
    else:
        print(f"\n{RED}❌ Some tests failed. PostgreSQL integration needs fixing.{NC}")
        
        # Provide specific fixes
        if not results["environment"]:
            print(f"\n{YELLOW}Fix: Set environment variables or check .env file{NC}")
        
        if not results["sqlite_not_used"]:
            print(f"\n{YELLOW}Fix: Stop processes using SQLite and archive the file{NC}")
            print(f"     ./fix_database_flow.sh")
        
        if not results["api_running"]:
            print(f"\n{YELLOW}Fix: Start the API server{NC}")
            print(f"     ./start_api_postgresql.sh")
        
        if not results["sheets_sync"]:
            print(f"\n{YELLOW}Fix: Start sheets sync daemon{NC}")
            print(f"     ./manage_sheets_sync.sh start -d")
        
        if results["api_running"] and not results["job_in_postgresql"]:
            print(f"\n{RED}CRITICAL: API is running but jobs are not going to PostgreSQL!{NC}")
            print(f"{YELLOW}This usually means EnhancedDatabaseManager is still using SQLite.{NC}")
            print(f"{YELLOW}Check api/services/job_service.py and database adapter.{NC}")

if __name__ == "__main__":
    main()
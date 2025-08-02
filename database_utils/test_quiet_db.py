#!/usr/bin/env python3
"""
Test script to verify quiet database initialization works
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=== Testing Quiet Database Initialization ===")
print("This should show NO database initialization logs.")
print()

# Test with quiet mode
print("1. Testing with quiet mode:")
from src.utils.quiet_mode import quiet_database_init
from src.database import DatabaseManager

with quiet_database_init():
    print("   Initializing DatabaseManager with quiet mode...")
    db = DatabaseManager()
    print("   ✅ DatabaseManager initialized silently")

print()

# Test normal mode (should show logs)
print("2. Testing normal mode (should show logs):")
print("   Initializing DatabaseManager normally...")
import logging
logging.getLogger('src.database.factory').setLevel(logging.DEBUG)
db2 = DatabaseManager()
print("   ✅ DatabaseManager initialized with logs")

print()
print("=== Test Complete ===")
print("If you see database initialization logs only in section 2, the fix works!")
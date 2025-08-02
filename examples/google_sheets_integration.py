#!/usr/bin/env python3
"""
Google Sheets Integration Example for AutoTrainX

This example shows how to set up and use the Google Sheets synchronization
feature to automatically sync training data to a Google Spreadsheet.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.sheets_sync import setup_sheets_sync, get_sheets_sync_status
from src.sheets_sync.integration import manual_full_sync, test_connection


async def main():
    """Main example function."""
    print("=== AutoTrainX Google Sheets Integration Example ===\n")
    
    # Example 1: Quick setup with OAuth2
    print("1. Setting up Google Sheets sync with OAuth2...")
    try:
        result = await setup_sheets_sync(
            spreadsheet_id="YOUR_SPREADSHEET_ID_HERE",
            auth_type="oauth2"
        )
        
        if result.success:
            print(f"✅ Success: {result.message}")
        else:
            print(f"❌ Error: {result.message}")
    except Exception as e:
        print(f"❌ Setup failed: {e}")
    
    print("\n" + "-"*50 + "\n")
    
    # Example 2: Test the connection
    print("2. Testing Google Sheets connection...")
    try:
        test_result = await test_connection()
        if test_result:
            print("✅ Connection test successful!")
        else:
            print("❌ Connection test failed!")
    except Exception as e:
        print(f"❌ Connection test error: {e}")
    
    print("\n" + "-"*50 + "\n")
    
    # Example 3: Check sync status
    print("3. Checking sync status...")
    try:
        status = await get_sheets_sync_status()
        print(f"Sync enabled: {status['enabled']}")
        print(f"Service running: {status['running']}")
        if status['running']:
            print(f"Queue size: {status['queue_size']}")
            print(f"Workers: {status['workers']}")
            print(f"Health: {status['health']['healthy']}")
    except Exception as e:
        print(f"❌ Status check error: {e}")
    
    print("\n" + "-"*50 + "\n")
    
    # Example 4: Manual full sync
    print("4. Performing manual full sync...")
    try:
        sync_result = await manual_full_sync()
        if sync_result.success:
            print(f"✅ Sync completed: {sync_result.message}")
            print(f"   Records synced: {sync_result.data.get('total_synced', 0)}")
        else:
            print(f"❌ Sync failed: {sync_result.message}")
    except Exception as e:
        print(f"❌ Manual sync error: {e}")
    
    print("\n" + "-"*50 + "\n")
    
    # Example 5: Using with training pipeline
    print("5. Example: Integrating with training pipeline...")
    print("""
    # In your training script:
    from src.pipeline.pipeline import AutoTrainPipeline
    from src.sheets_sync import get_sheets_sync_service
    
    # Initialize sync service
    sync_service = await get_sheets_sync_service()
    if sync_service:
        print("Google Sheets sync is active!")
    
    # Run your training - sync happens automatically
    pipeline = AutoTrainPipeline(config)
    result = await pipeline.run()
    
    # The database changes will be automatically synced to Google Sheets
    """)
    
    print("\n=== Configuration Tips ===")
    print("""
    1. Service Account Setup:
       - Create service account at https://console.cloud.google.com/
       - Download JSON key and save to: settings/google_credentials.json
       - Share your Google Sheet with the service account email
    
    2. OAuth2 Setup:
       - Create OAuth2 credentials at https://console.cloud.google.com/
       - Download credentials.json
       - First run will open browser for authorization
    
    3. config.json structure:
       {
         "google_sheets_sync": {
           "enabled": true,
           "spreadsheet_id": "your-spreadsheet-id",
           "credentials_path": "settings/google_credentials.json"
         }
       }
    
    4. Spreadsheet Setup:
       - Create two sheets: "Executions" and "Variations"
       - The system will auto-create headers on first sync
    """)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
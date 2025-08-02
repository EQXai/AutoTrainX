"""Example script demonstrating Google Sheets synchronization setup."""

import asyncio
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sheets_sync import setup_sheets_sync, get_sheets_sync_status, get_setup_help


async def main():
    """Main example function."""
    print("Google Sheets Sync Example")
    print("=" * 50)
    
    # Get setup help
    print("\n1. Getting setup help...")
    help_info = get_setup_help()
    print(f"Configuration file location: {help_info['config_file_location']}")
    print("Authentication types available:")
    for auth_type, info in help_info['auth_types'].items():
        print(f"  - {auth_type}: {info['description']}")
    
    # Check current status
    print("\n2. Checking current sync status...")
    try:
        status = await get_sheets_sync_status()
        print(f"Sync enabled: {status.get('enabled', False)}")
        print(f"Service running: {status.get('running', False)}")
        
        if status.get('error'):
            print(f"Error: {status['error']}")
    
    except Exception as e:
        print(f"Could not get status: {e}")
    
    # Example setup (commented out - requires actual credentials)
    print("\n3. Example setup (commented out):")
    print("""
    # To set up Google Sheets sync, uncomment and modify the following:
    
    # For OAuth2 authentication:
    # result = await setup_sheets_sync(
    #     spreadsheet_id="YOUR_SPREADSHEET_ID_HERE",
    #     auth_type="oauth2",
    #     credentials_path="/path/to/your/credentials.json"
    # )
    
    # For Service Account authentication:
    # result = await setup_sheets_sync(
    #     spreadsheet_id="YOUR_SPREADSHEET_ID_HERE", 
    #     auth_type="service_account",
    #     service_account_path="/path/to/your/service-account-key.json"
    # )
    
    # print(f"Setup result: {result}")
    """)
    
    print("\n4. Setup steps:")
    print("   a. Create a Google Spreadsheet")
    print("   b. Set up authentication (OAuth2 or Service Account)")
    print("   c. Run the setup with your credentials")
    print("   d. The system will automatically sync training data to your spreadsheet")
    
    print("\nExample completed!")


if __name__ == "__main__":
    asyncio.run(main())
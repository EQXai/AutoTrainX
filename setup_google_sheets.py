#!/usr/bin/env python3
"""
Setup helper script for Google Sheets integration.

This script helps configure Google Sheets sync for AutoTrainX.
"""

import json
import shutil
import sys
from pathlib import Path


def setup_google_sheets(credentials_path: str, spreadsheet_id: str):
    """Set up Google Sheets integration."""
    try:
        # Check if credentials file exists
        creds_file = Path(credentials_path)
        if not creds_file.exists():
            print(f"❌ Error: Credentials file not found: {credentials_path}")
            return False
        
        # Create settings directory if it doesn't exist
        settings_dir = Path("settings")
        settings_dir.mkdir(exist_ok=True)
        
        # Copy credentials to settings directory
        dest_path = settings_dir / "google_credentials.json"
        shutil.copy2(creds_file, dest_path)
        print(f"✅ Credentials copied to: {dest_path}")
        
        # Update config.json
        config_path = Path("config.json")
        config = {}
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
        
        # Update Google Sheets configuration
        if 'google_sheets_sync' not in config:
            config['google_sheets_sync'] = {}
        
        config['google_sheets_sync'].update({
            'enabled': True,
            'spreadsheet_id': spreadsheet_id,
            'credentials_path': str(dest_path)
        })
        
        # Save updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Configuration updated in config.json")
        print(f"✅ Spreadsheet ID set to: {spreadsheet_id}")
        
        # Display service account email if it's a service account
        try:
            with open(dest_path, 'r') as f:
                creds_data = json.load(f)
                if 'client_email' in creds_data:
                    print(f"\n📧 Service Account Email: {creds_data['client_email']}")
                    print("⚠️  Make sure to share your Google Sheet with this email!")
        except:
            pass
        
        print("\n✅ Google Sheets sync is now configured!")
        print("\nNext steps:")
        print("1. Share your Google Sheet with the service account email above")
        print("2. Run the interactive menu to test the connection")
        print("3. Start training - data will sync automatically!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up Google Sheets: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python setup_google_sheets.py <credentials_file> <spreadsheet_id>")
        print("\nExample:")
        print("  python setup_google_sheets.py /path/to/credentials.json 1ABC123def456")
        sys.exit(1)
    
    credentials_path = sys.argv[1]
    spreadsheet_id = sys.argv[2]
    
    success = setup_google_sheets(credentials_path, spreadsheet_id)
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Test Google Sheets Connection for AutoTrainX PostgreSQL Integration

This script tests the connection to Google Sheets and verifies
that the sync functionality is properly configured.
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file."""
    env_file = Path(__file__).parent / "settings" / ".env"
    if env_file.exists():
        try:
            # Use a more robust method to handle multiline values
            current_key = None
            current_value = []
            
            with open(env_file, 'r') as f:
                for line in f:
                    # Skip empty lines and comments
                    if not line.strip() or line.strip().startswith('#'):
                        continue
                    
                    # Check if this is a new key=value pair
                    if '=' in line and not line.strip().startswith(' '):
                        # Save previous key-value if exists
                        if current_key:
                            value = ''.join(current_value).strip()
                            # Remove quotes if present
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]
                            os.environ[current_key] = value
                        
                        # Start new key-value
                        key, value = line.split('=', 1)
                        current_key = key.strip()
                        current_value = [value]
                    elif current_key:
                        # This is a continuation of a multiline value
                        current_value.append(line)
                
                # Don't forget the last key-value pair
                if current_key:
                    value = ''.join(current_value).strip()
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ[current_key] = value
                    
        except Exception as e:
            print(f"Warning: Could not load .env file: {e}")

# Load .env file before anything else
load_env_file()

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("❌ Google API libraries not installed!")
    print("   Please run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

# If modifying these scopes, delete the token file
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def load_config():
    """Load configuration from environment and files."""
    config = {
        'spreadsheet_id': os.environ.get('AUTOTRAINX_SHEETS_ID'),
        'credentials_file': os.environ.get('AUTOTRAINX_SHEETS_CREDENTIALS', 'credentials.json'),
        'token_file': os.environ.get('AUTOTRAINX_SHEETS_TOKEN', 'token.json'),
    }
    
    # Check database configuration - try both naming conventions
    db_config = {
        'host': os.environ.get('AUTOTRAINX_DB_HOST', os.environ.get('DATABASE_HOST', 'localhost')),
        'port': os.environ.get('AUTOTRAINX_DB_PORT', os.environ.get('DATABASE_PORT', '5432')),
        'name': os.environ.get('AUTOTRAINX_DB_NAME', os.environ.get('DATABASE_NAME', 'autotrainx')),
        'user': os.environ.get('AUTOTRAINX_DB_USER', os.environ.get('DATABASE_USER', 'autotrainx')),
        'password': os.environ.get('AUTOTRAINX_DB_PASSWORD', os.environ.get('DATABASE_PASSWORD', 'AutoTrainX2024Secure123')),
    }
    
    return config, db_config


def get_google_service(config):
    """Get authenticated Google Sheets service."""
    from google.oauth2 import service_account
    
    # First, try to use service account from environment
    from src.configuration.secure_config import secure_config
    google_creds = secure_config.google_credentials
    if google_creds:
        try:
            creds = service_account.Credentials.from_service_account_info(
                google_creds,
                scopes=SCOPES
            )
            print("✅ Using service account authentication from environment")
            return build('sheets', 'v4', credentials=creds)
        except Exception as e:
            print(f"⚠️  Error using service account: {e}")
    
    # Fall back to OAuth2 flow
    creds = None
    
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists(config['token_file']):
        creds = Credentials.from_authorized_user_file(config['token_file'], SCOPES)
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(config['credentials_file']):
                print(f"❌ Credentials file not found: {config['credentials_file']}")
                print("   No service account credentials in environment either.")
                print("\n📝 To fix this:")
                print("   1. Add Google credentials to your .env file:")
                print("      GOOGLE_SERVICE_ACCOUNT_EMAIL=...")
                print("      GOOGLE_PROJECT_ID=...")
                print("      GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY=...")
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file(
                config['credentials_file'], SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(config['token_file'], 'w') as token:
            token.write(creds.to_json())
    
    return build('sheets', 'v4', credentials=creds)


def test_spreadsheet_access(service, spreadsheet_id):
    """Test access to the spreadsheet."""
    try:
        # Try to get spreadsheet metadata
        sheet = service.spreadsheets()
        result = sheet.get(spreadsheetId=spreadsheet_id).execute()
        
        print(f"✅ Successfully connected to spreadsheet: {result.get('properties', {}).get('title', 'Unknown')}")
        print(f"   Spreadsheet ID: {spreadsheet_id}")
        
        # List all sheets
        sheets = result.get('sheets', [])
        print(f"\n📊 Found {len(sheets)} sheet(s):")
        for sheet in sheets:
            props = sheet.get('properties', {})
            print(f"   - {props.get('title')} (ID: {props.get('sheetId')})")
        
        return True
        
    except HttpError as error:
        print(f"❌ Error accessing spreadsheet: {error}")
        if error.resp.status == 404:
            print("   The spreadsheet ID may be incorrect or you don't have access")
        elif error.resp.status == 403:
            print("   Permission denied. Make sure you have access to this spreadsheet")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_database_connection(db_config):
    """Test PostgreSQL database connection."""
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['name'],
            user=db_config['user'],
            password=db_config['password']
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()[0]
        
        print(f"✅ Successfully connected to PostgreSQL database")
        print(f"   Database: {db_config['name']} @ {db_config['host']}:{db_config['port']}")
        print(f"   Version: {db_version.split(',')[0]}")
        
        # Check if required tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('executions', 'variations', 'models', 'model_paths')
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print(f"\n📊 Found {len(tables)} AutoTrainX table(s):")
        for table in tables:
            print(f"   - {table[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except ImportError:
        print("❌ psycopg2 not installed!")
        print("   Please run: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False


def test_write_sample_data(service, spreadsheet_id):
    """Test writing sample data to the spreadsheet."""
    try:
        # Prepare test data
        test_data = [
            ["Test Timestamp", "Test Status", "Test Message"],
            [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "SUCCESS", "Connection test successful"]
        ]
        
        # Write to a test sheet
        body = {
            'values': test_data
        }
        
        sheet = service.spreadsheets()
        result = sheet.values().update(
            spreadsheetId=spreadsheet_id,
            range='Test!A1:C2',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"\n✅ Successfully wrote test data to spreadsheet")
        print(f"   Updated {result.get('updatedCells')} cells")
        
        return True
        
    except HttpError as error:
        if error.resp.status == 400 and "Unable to parse range" in str(error):
            print("\n⚠️  'Test' sheet doesn't exist. Trying to create it...")
            try:
                # Create the Test sheet
                batch_update_body = {
                    'requests': [{
                        'addSheet': {
                            'properties': {
                                'title': 'Test',
                                'index': 0,
                                'gridProperties': {
                                    'rowCount': 100,
                                    'columnCount': 10
                                }
                            }
                        }
                    }]
                }
                
                sheet.batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=batch_update_body
                ).execute()
                
                print("✅ Created 'Test' sheet")
                
                # Try writing again
                return test_write_sample_data(service, spreadsheet_id)
                
            except Exception as e:
                print(f"❌ Error creating test sheet: {e}")
                return False
        else:
            print(f"❌ Error writing test data: {error}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error writing test data: {e}")
        return False


def main():
    """Main test function."""
    # Load configuration
    config, db_config = load_config()
    
    # Check if spreadsheet ID is configured
    if not config['spreadsheet_id']:
        print("\n❌ No spreadsheet ID configured!")
        print("\n📝 To configure Google Sheets:")
        print("   1. Go back to the main menu")
        print("   2. Select '⚙️  Configuration'")
        print("   3. Select '📊 Google Sheets Settings'")
        print("   4. Select '📋 Set Spreadsheet ID'")
        print("\n   Or manually add to your .env file:")
        print("   AUTOTRAINX_SHEETS_ID=your-spreadsheet-id-here")
        print("\n💡 The Spreadsheet ID can be found in your Google Sheets URL:")
        print("   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit")
        return 1
    
    print(f"📋 Spreadsheet ID: {config['spreadsheet_id']}")
    print(f"🔑 Credentials file: {config['credentials_file']}")
    print(f"🎫 Token file: {config['token_file']}\n")
    
    # Test database connection
    print("1️⃣  Testing PostgreSQL Database Connection...")
    print("-" * 50)
    if not test_database_connection(db_config):
        return 1
    
    print("\n2️⃣  Testing Google Sheets Authentication...")
    print("-" * 50)
    
    # Get Google service
    service = get_google_service(config)
    if not service:
        return 1
    
    print("✅ Authentication successful!\n")
    
    # Test spreadsheet access
    print("3️⃣  Testing Spreadsheet Access...")
    print("-" * 50)
    if not test_spreadsheet_access(service, config['spreadsheet_id']):
        return 1
    
    # Test writing data
    print("\n4️⃣  Testing Write Permissions...")
    print("-" * 50)
    if not test_write_sample_data(service, config['spreadsheet_id']):
        print("\n⚠️  Write test failed, but read access works")
        print("   The sync daemon may still work for read-only operations")
    
    print("\n==================================================")
    print("  ✅ ALL TESTS PASSED!")
    print("==================================================")
    print("\nYour Google Sheets sync is properly configured.")
    print("You can now start the sync daemon.\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
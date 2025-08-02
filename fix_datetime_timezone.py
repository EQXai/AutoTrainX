#!/usr/bin/env python3
"""
Fix datetime timezone issues in AutoTrainX
Ensures all datetime objects are timezone-aware
"""

import os
import sys
from datetime import datetime, timezone
import pytz

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def patch_datetime_issues():
    """Monkey patch datetime operations to handle timezone issues"""
    
    # Import the database models
    try:
        from src.database.models import Execution, ExecutionVariation
        from src.database.manager_v2 import DatabaseManagerV2
        
        # Patch the Execution model's datetime fields
        original_init = Execution.__init__
        
        def patched_init(self, **kwargs):
            # Ensure all datetime fields are timezone-aware
            datetime_fields = ['created_at', 'updated_at', 'started_at', 'completed_at']
            
            for field in datetime_fields:
                if field in kwargs and kwargs[field] is not None:
                    dt = kwargs[field]
                    if hasattr(dt, 'tzinfo') and dt.tzinfo is None:
                        # Convert naive datetime to UTC
                        kwargs[field] = dt.replace(tzinfo=timezone.utc)
            
            original_init(self, **kwargs)
        
        Execution.__init__ = patched_init
        
        print("✅ Patched Execution model for timezone handling")
        
    except ImportError as e:
        print(f"⚠️  Could not import models: {e}")

def create_timezone_fix_script():
    """Create a script to fix timezone issues in the database"""
    
    fix_script = '''#!/usr/bin/env python3
"""
Fix timezone issues in PostgreSQL database
"""

import os
import psycopg2
from datetime import timezone

# Database configuration
DB_CONFIG = {
    'host': os.getenv('AUTOTRAINX_DB_HOST', 'localhost'),
    'port': os.getenv('AUTOTRAINX_DB_PORT', '5432'),
    'database': os.getenv('AUTOTRAINX_DB_NAME', 'autotrainx'),
    'user': os.getenv('AUTOTRAINX_DB_USER', 'autotrainx'),
    'password': os.getenv('AUTOTRAINX_DB_PASSWORD', '1234')
}

def fix_timezone_in_database():
    """Update all datetime columns to have timezone information"""
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        print("🔧 Fixing timezone issues in database...")
        
        # Get all timestamp columns
        cur.execute("""
            SELECT table_name, column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND data_type = 'timestamp without time zone'
        """)
        
        columns = cur.fetchall()
        
        if not columns:
            print("✅ No timestamp columns without timezone found")
            return
        
        for table, column in columns:
            print(f"  Updating {table}.{column}...")
            
            # Convert column to timestamp with timezone
            try:
                cur.execute(f"""
                    ALTER TABLE {table} 
                    ALTER COLUMN {column} 
                    TYPE timestamp with time zone 
                    USING {column} AT TIME ZONE 'UTC'
                """)
                conn.commit()
                print(f"    ✅ Converted {table}.{column} to timezone-aware")
            except Exception as e:
                print(f"    ❌ Error converting {table}.{column}: {e}")
                conn.rollback()
        
        cur.close()
        conn.close()
        print("✅ Database timezone fix completed")
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")

if __name__ == "__main__":
    # Load .env if exists
    env_file = os.path.join(os.path.dirname(__file__), 'database_utils/.env')
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    fix_timezone_in_database()
'''
    
    with open('fix_postgresql_timezone.py', 'w') as f:
        f.write(fix_script)
    
    os.chmod('fix_postgresql_timezone.py', 0o755)
    print("✅ Created fix_postgresql_timezone.py")

def create_datetime_wrapper():
    """Create a wrapper for datetime operations"""
    
    wrapper_content = '''#!/usr/bin/env python3
"""
DateTime wrapper to ensure timezone consistency
Add this to your imports to fix timezone issues
"""

from datetime import datetime as _datetime, timezone
import pytz

class datetime(_datetime):
    """Wrapper around datetime to ensure timezone awareness"""
    
    @classmethod
    def now(cls, tz=None):
        """Always return timezone-aware datetime"""
        if tz is None:
            tz = timezone.utc
        return super().now(tz)
    
    @classmethod
    def utcnow(cls):
        """Return timezone-aware UTC datetime"""
        return cls.now(timezone.utc)
    
    def replace(self, **kwargs):
        """Ensure replaced datetime keeps timezone"""
        if 'tzinfo' not in kwargs and self.tzinfo is None:
            kwargs['tzinfo'] = timezone.utc
        return super().replace(**kwargs)

# Monkey patch the original datetime
import sys
sys.modules['datetime'].datetime = datetime

print("✅ DateTime wrapper installed - all datetimes will be timezone-aware")
'''
    
    with open('datetime_wrapper.py', 'w') as f:
        f.write(wrapper_content)
    
    print("✅ Created datetime_wrapper.py")

def main():
    print("🔧 AutoTrainX Timezone Fix Utility")
    print("=" * 50)
    
    # Create fix scripts
    create_timezone_fix_script()
    create_datetime_wrapper()
    
    print("\n📝 Instructions:")
    print("1. Fix existing database timezone issues:")
    print("   python fix_postgresql_timezone.py")
    print()
    print("2. Add to your main.py or api_server.py:")
    print("   import datetime_wrapper  # Add at the top")
    print()
    print("3. Or manually fix in your code:")
    print("   from datetime import datetime, timezone")
    print("   # Always use timezone-aware datetimes:")
    print("   datetime.now(timezone.utc)")
    print()
    print("4. For existing naive datetimes:")
    print("   if dt.tzinfo is None:")
    print("       dt = dt.replace(tzinfo=timezone.utc)")

if __name__ == "__main__":
    main()
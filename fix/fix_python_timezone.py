#!/usr/bin/env python3
"""
Fix Python timezone issues in AutoTrainX
Patches datetime operations to always use timezone-aware datetimes
"""

import os
import sys
from datetime import datetime, timezone

def find_and_fix_timezone_issues():
    """Find Python files with potential timezone issues"""
    
    print("🔍 Searching for timezone issues in Python files...")
    
    issues_found = []
    files_to_check = []
    
    # Find all Python files
    for root, dirs, files in os.walk('.'):
        # Skip virtual environments and cache
        if 'venv' in root or '__pycache__' in root or '.git' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                files_to_check.append(os.path.join(root, file))
    
    # Patterns that might cause timezone issues
    problematic_patterns = [
        'datetime.now()',
        'datetime.utcnow()',
        'datetime.today()',
        '.replace(tzinfo=None)',
        'datetime.fromtimestamp(',
    ]
    
    for filepath in files_to_check:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            for i, line in enumerate(lines, 1):
                for pattern in problematic_patterns:
                    if pattern in line and 'timezone' not in line:
                        issues_found.append({
                            'file': filepath,
                            'line': i,
                            'content': line.strip(),
                            'pattern': pattern
                        })
        except Exception as e:
            continue
    
    if issues_found:
        print(f"\n⚠️  Found {len(issues_found)} potential timezone issues:\n")
        for issue in issues_found[:10]:  # Show first 10
            print(f"📄 {issue['file']}:{issue['line']}")
            print(f"   {issue['content']}")
            print(f"   Pattern: {issue['pattern']}")
            print()
    else:
        print("✅ No obvious timezone issues found in Python files")
    
    return issues_found

def create_timezone_patch():
    """Create a patch file to fix common timezone issues"""
    
    patch_content = '''#!/usr/bin/env python3
"""
Timezone patch for AutoTrainX
Import this at the beginning of your main script to fix timezone issues
"""

import datetime as _datetime_module
from datetime import timezone
import logging

logger = logging.getLogger(__name__)

# Store original datetime class
_original_datetime = _datetime_module.datetime

class DatetimeWithTimezone(_original_datetime):
    """Patched datetime that always includes timezone"""
    
    @classmethod
    def now(cls, tz=None):
        """Always return timezone-aware datetime"""
        if tz is None:
            tz = timezone.utc
            logger.debug("datetime.now() called without timezone, using UTC")
        return _original_datetime.now(tz)
    
    @classmethod
    def utcnow(cls):
        """Return timezone-aware UTC datetime"""
        logger.debug("datetime.utcnow() called, returning timezone-aware UTC")
        return cls.now(timezone.utc)
    
    @classmethod
    def today(cls):
        """Return timezone-aware date"""
        logger.debug("datetime.today() called, returning timezone-aware UTC")
        return cls.now(timezone.utc).date()
    
    @classmethod
    def fromtimestamp(cls, timestamp, tz=None):
        """Always return timezone-aware datetime from timestamp"""
        if tz is None:
            tz = timezone.utc
            logger.debug("datetime.fromtimestamp() called without timezone, using UTC")
        return _original_datetime.fromtimestamp(timestamp, tz)

# Apply the patch
_datetime_module.datetime = DatetimeWithTimezone

print("✅ Timezone patch applied - all datetime operations will be timezone-aware")

# Also patch common imports
import sys
if 'datetime' in sys.modules:
    sys.modules['datetime'].datetime = DatetimeWithTimezone
'''
    
    with open('timezone_patch.py', 'w') as f:
        f.write(patch_content)
    
    print("✅ Created timezone_patch.py")

def create_quick_fix():
    """Create a quick fix script"""
    
    fix_script = '''#!/usr/bin/env python3
"""
Quick fix for timezone issues
Run this to patch the running AutoTrainX instance
"""

import os
import sys

# Add this to the beginning of api_server.py or main.py
TIMEZONE_FIX = """
# Timezone fix
from datetime import datetime, timezone
import datetime as dt_module

# Monkey patch datetime to always use timezone
_original_datetime = dt_module.datetime

class TZAwareDatetime(_original_datetime):
    @classmethod
    def now(cls, tz=None):
        if tz is None:
            tz = timezone.utc
        return _original_datetime.now(tz)
    
    @classmethod
    def utcnow(cls):
        return cls.now(timezone.utc)

dt_module.datetime = TZAwareDatetime
"""

def add_timezone_fix_to_file(filepath):
    """Add timezone fix to a Python file"""
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    if 'TZAwareDatetime' in content:
        print(f"✅ Timezone fix already present in {filepath}")
        return True
    
    # Find the right place to insert (after imports)
    lines = content.split('\\n')
    insert_index = 0
    
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_index = i + 1
        elif line and not line.startswith('#') and insert_index > 0:
            break
    
    # Insert the fix
    lines.insert(insert_index, TIMEZONE_FIX)
    
    with open(filepath, 'w') as f:
        f.write('\\n'.join(lines))
    
    print(f"✅ Added timezone fix to {filepath}")
    return True

if __name__ == "__main__":
    print("🔧 Quick Timezone Fix for AutoTrainX")
    print("=" * 50)
    
    # Try to fix common entry points
    files_to_fix = [
        'api_server.py',
        'main.py',
        'src/database/manager_v2.py',
        'src/core/job_manager.py',
    ]
    
    fixed_count = 0
    for file in files_to_fix:
        if os.path.exists(file):
            if add_timezone_fix_to_file(file):
                fixed_count += 1
    
    if fixed_count > 0:
        print(f"\\n✅ Fixed {fixed_count} files")
        print("🔄 Please restart AutoTrainX for changes to take effect")
    else:
        print("\\n⚠️  No files were modified")
        print("You may need to manually add the timezone fix")
'''
    
    with open('quick_timezone_fix.py', 'w') as f:
        f.write(fix_script)
    
    os.chmod('quick_timezone_fix.py', 0o755)
    print("✅ Created quick_timezone_fix.py")

def main():
    print("🔧 Python Timezone Fix for AutoTrainX")
    print("=" * 50)
    
    # Find issues
    issues = find_and_fix_timezone_issues()
    
    # Create fixes
    create_timezone_patch()
    create_quick_fix()
    
    print("\n📝 To fix the timezone issues:")
    print("\n1. Quick fix (recommended):")
    print("   python quick_timezone_fix.py")
    print("   # Then restart AutoTrainX")
    
    print("\n2. Manual patch:")
    print("   # Add to the top of api_server.py or main.py:")
    print("   import timezone_patch")
    
    print("\n3. Fix specific datetime calls:")
    print("   # Replace:")
    print("   datetime.now()  →  datetime.now(timezone.utc)")
    print("   datetime.utcnow()  →  datetime.now(timezone.utc)")
    
    if issues:
        print(f"\n⚠️  Found {len(issues)} files that may need fixing")

if __name__ == "__main__":
    main()
# Database Migration Guide - Phase 2 Complete

## Overview

Phase 2 of the SQLite to PostgreSQL migration has been completed. This phase focused on updating all database managers and API endpoints to use the new abstraction layer, enabling full dual-database support.

## What's Been Implemented

### 1. Updated Database Managers
- **manager_v2.py** - DatabaseManager with factory pattern support
- **enhanced_manager_v2.py** - EnhancedDatabaseManager with PostgreSQL optimizations
- **connection_pool_v2.py** - PooledDatabaseManager with database-specific pooling

### 2. API Endpoints Migration
- **dataset_paths_v2.py** - Replaced direct sqlite3 usage with SQLAlchemy ORM
- Full compatibility with both SQLite and PostgreSQL

### 3. Database-Specific Optimizations
- **schema_improvements_v2.py** - Conditional optimizations based on database type
- **transactions_v2.py** - Multi-database transaction management with retry logic

### 4. Migration Tool
- **migrate_to_postgresql.py** - Complete data migration script
- Supports batch processing and verification
- Handles all tables including cache and auxiliary tables

### 5. Backward Compatibility
- Updated `__init__.py` with fallback imports
- Existing code continues to work without changes
- Gradual migration path available

## How to Use

### Option 1: Continue Using SQLite (Default)
No changes required. The system continues to use SQLite by default.

### Option 2: Switch to PostgreSQL

1. **Set up PostgreSQL database:**
   ```bash
   createdb autotrainx
   createuser autotrainx -P  # Enter password when prompted
   ```

2. **Configure environment:**
   ```bash
   export AUTOTRAINX_DB_TYPE=postgresql
   export AUTOTRAINX_DB_HOST=localhost
   export AUTOTRAINX_DB_PORT=5432
   export AUTOTRAINX_DB_NAME=autotrainx
   export AUTOTRAINX_DB_USER=autotrainx
   export AUTOTRAINX_DB_PASSWORD=your_secure_password
   ```

3. **Migrate existing data (optional):**
   ```bash
   python src/database/migrate_to_postgresql.py \
     --source DB/executions.db \
     --target postgresql://autotrainx:password@localhost/autotrainx
   ```

### Option 3: Use Configuration File

Create `db_config.json`:
```json
{
  "type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "database": "autotrainx",
  "username": "autotrainx",
  "password": "your_secure_password",
  "pool": {
    "size": 20,
    "max_overflow": 40
  }
}
```

Then:
```bash
export AUTOTRAINX_DB_CONFIG=/path/to/db_config.json
```

## Migration Script Usage

The migration script supports various options:

```bash
# Basic migration
python src/database/migrate_to_postgresql.py \
  --source /path/to/sqlite.db \
  --target postgresql://user:pass@host/db

# Drop existing tables first
python src/database/migrate_to_postgresql.py \
  --source /path/to/sqlite.db \
  --target postgresql://user:pass@host/db \
  --drop-existing

# Custom batch size
python src/database/migrate_to_postgresql.py \
  --source /path/to/sqlite.db \
  --target postgresql://user:pass@host/db \
  --batch-size 5000

# Using environment variables
export SOURCE_DB_PATH=/path/to/sqlite.db
export TARGET_DB_URL=postgresql://user:pass@host/db
python src/database/migrate_to_postgresql.py
```

## Performance Comparisons

### SQLite
- **Pros:** Zero configuration, embedded, fast for single-user
- **Cons:** Database-level locking, limited concurrency
- **Best for:** Development, single-user deployments

### PostgreSQL
- **Pros:** Row-level locking, JSONB indexing, better concurrency
- **Cons:** Requires server setup, network overhead
- **Best for:** Production, multi-user deployments

## Database-Specific Features

### SQLite Features Used
- WAL mode for concurrency
- Partial indexes
- Custom cache configuration
- Incremental auto-vacuum

### PostgreSQL Features Available
- JSONB with GIN indexes
- Materialized views
- Advisory locks
- Concurrent index creation
- Parallel query execution

## Code Changes Required

### For New Code
Use the factory pattern:
```python
from src.database import DatabaseManager, DatabaseConfig

# Automatically uses configured database
db_manager = DatabaseManager()

# Or specify explicitly
config = DatabaseConfig(
    db_type='postgresql',
    db_url='postgresql://...'
)
db_manager = DatabaseManager(config)
```

### For API Endpoints
Import the v2 versions:
```python
# Old
from api.routes.dataset_paths import router

# New
from api.routes.dataset_paths_v2 import router
```

## Testing Both Databases

Run tests with different databases:
```bash
# Test with SQLite
export AUTOTRAINX_DB_TYPE=sqlite
pytest tests/

# Test with PostgreSQL
export AUTOTRAINX_DB_TYPE=postgresql
pytest tests/
```

## Monitoring and Maintenance

### Connection Pool Monitoring
```python
from src.database import PooledDatabaseManager

manager = PooledDatabaseManager()
status = manager.get_pool_status()
print(f"Active connections: {status['checked_out']}/{status['size']}")
```

### Database Maintenance
```python
from src.database import EnhancedDatabaseManager

manager = EnhancedDatabaseManager()
manager.perform_maintenance()  # Runs VACUUM, ANALYZE, etc.
```

## Troubleshooting

### Common Issues

1. **"database is locked" errors (SQLite)**
   - Increase busy timeout: `AUTOTRAINX_DB_BUSY_TIMEOUT=10000`
   - Check for long-running transactions

2. **Connection pool exhausted (PostgreSQL)**
   - Increase pool size: `AUTOTRAINX_DB_POOL_SIZE=30`
   - Check for connection leaks

3. **Slow queries**
   - Run maintenance: `manager.perform_maintenance()`
   - Check missing indexes

### Debug Mode
Enable SQL logging:
```bash
export AUTOTRAINX_DB_ECHO=true
```

## Next Steps

1. **Update application code** to use new managers
2. **Test thoroughly** with both databases
3. **Monitor performance** in production
4. **Plan migration window** if switching to PostgreSQL

## Files Created/Modified in Phase 2

### New Files
- `/src/database/manager_v2.py`
- `/src/database/enhanced_manager_v2.py`
- `/src/database/connection_pool_v2.py`
- `/src/database/schema_improvements_v2.py`
- `/src/database/transactions_v2.py`
- `/src/database/migrate_to_postgresql.py`
- `/api/routes/dataset_paths_v2.py`

### Modified Files
- `/src/database/__init__.py` - Updated imports with fallback
- `requirements.txt` - Added psycopg2-binary

## Summary

The AutoTrainX database layer now supports both SQLite and PostgreSQL with:
- ✅ Full backward compatibility
- ✅ Easy configuration switching
- ✅ Database-specific optimizations
- ✅ Complete data migration tools
- ✅ Production-ready connection pooling
- ✅ Comprehensive error handling

The system is ready for gradual migration from SQLite to PostgreSQL based on deployment needs.
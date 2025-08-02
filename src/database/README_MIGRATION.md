# Database Migration Guide - Phase 1 Complete

## Overview

Phase 1 of the SQLite to PostgreSQL migration has been completed. This phase focused on creating the abstraction layer that allows AutoTrainX to support both SQLite and PostgreSQL databases.

## What's Been Implemented

### 1. Database Dialect System
- **Abstract base class** (`AbstractDialect`) defining the interface
- **SQLiteDialect** - Maintains all current SQLite optimizations
- **PostgreSQLDialect** - Implements PostgreSQL-specific features

### 2. Database Factory
- **DatabaseFactory** - Creates engines with appropriate dialect
- **DatabaseConfig** - Configuration management
- **Environment-based configuration** - Easy switching between databases

### 3. Multi-Database Models
- **models_v2.py** - Updated models with conditional types
- **JSON columns** - Native JSONB for PostgreSQL, custom type for SQLite
- **DateTime columns** - Timezone-aware for PostgreSQL, ISO format for SQLite

### 4. Configuration System
- **Environment variables** for database selection
- **JSON configuration files** for advanced settings
- **Backward compatible** with existing SQLite setup

## How to Use

### SQLite (Default - No Changes Required)
The system continues to use SQLite by default. No configuration changes are needed.

### PostgreSQL Setup

1. **Install PostgreSQL dependencies:**
   ```bash
   pip install -r requirements.txt  # Now includes psycopg2-binary
   ```

2. **Set environment variables:**
   ```bash
   export AUTOTRAINX_DB_TYPE=postgresql
   export AUTOTRAINX_DB_HOST=localhost
   export AUTOTRAINX_DB_PORT=5432
   export AUTOTRAINX_DB_NAME=autotrainx
   export AUTOTRAINX_DB_USER=your_user
   export AUTOTRAINX_DB_PASSWORD=your_password
   ```

3. **Or use a configuration file:**
   ```bash
   export AUTOTRAINX_DB_CONFIG=/path/to/db_config.json
   ```

## Configuration Examples

### Environment Variables
```bash
# SQLite (default)
export AUTOTRAINX_DB_TYPE=sqlite
export AUTOTRAINX_DB_PATH=/path/to/database.db

# PostgreSQL
export AUTOTRAINX_DB_TYPE=postgresql
export AUTOTRAINX_DB_HOST=localhost
export AUTOTRAINX_DB_PORT=5432
export AUTOTRAINX_DB_NAME=autotrainx
export AUTOTRAINX_DB_USER=autotrainx
export AUTOTRAINX_DB_PASSWORD=secure_password

# Common options
export AUTOTRAINX_DB_ECHO=true  # Enable SQL logging
export AUTOTRAINX_DB_POOL_SIZE=20  # Connection pool size
```

### JSON Configuration File
See `db_config_example.json` for a complete example.

## Next Steps (Phase 2)

1. **Update Database Managers** to use the new factory
2. **Migrate API endpoints** to remove direct SQLite usage
3. **Create migration scripts** for data transfer
4. **Update tests** for dual database support

## Testing the New System

```python
from src.database.factory import DatabaseFactory, DatabaseConfig
from src.database.models_v2 import Base, Execution

# SQLite
sqlite_config = DatabaseConfig(
    db_type='sqlite',
    db_path='test.db'
)
sqlite_engine = DatabaseFactory.create_engine(sqlite_config)

# PostgreSQL
pg_config = DatabaseConfig(
    db_type='postgresql',
    db_url='postgresql://user:pass@localhost/testdb'
)
pg_engine = DatabaseFactory.create_engine(pg_config)

# Create tables (works with both)
Base.metadata.create_all(sqlite_engine)
Base.metadata.create_all(pg_engine)
```

## Important Notes

1. **No breaking changes** - Existing SQLite setup continues to work
2. **Gradual migration** - Can test PostgreSQL while using SQLite
3. **Performance maintained** - All SQLite optimizations preserved
4. **Type safety** - Conditional types ensure compatibility

## Files Created/Modified

### New Files
- `/src/database/dialects/` - Dialect implementations
- `/src/database/factory.py` - Engine factory
- `/src/database/config.py` - Configuration management
- `/src/database/models_v2.py` - Updated models
- `/src/database/db_config_example.json` - Config example

### Modified Files
- `requirements.txt` - Added psycopg2-binary

## Migration Checklist

- [x] Create dialect abstraction layer
- [x] Implement SQLite dialect
- [x] Implement PostgreSQL dialect
- [x] Create database factory
- [x] Update models for dual support
- [x] Add configuration system
- [x] Update requirements
- [ ] Update database managers
- [ ] Migrate API endpoints
- [ ] Create data migration tools
- [ ] Update documentation
- [ ] Add comprehensive tests
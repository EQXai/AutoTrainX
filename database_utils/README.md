# Database Utilities for AutoTrainX

This directory contains unified utilities for PostgreSQL database management.

## 🚀 Quick Start

### 1. Initial Setup
```bash
# Run the setup script to install and configure PostgreSQL
./setup_postgresql.sh
```

### 2. Database Management
```bash
# Launch the interactive PostgreSQL manager
python postgresql_manager.py
```

### 3. View Database
```bash
# Launch the Gradio web viewer
python pg_viewer.py
```

## 📁 Files Overview

### Main Scripts

- **`postgresql_manager.py`** - Unified management interface with interactive menu
  - Setup & Installation
  - Database Viewer (terminal)
  - Utilities & Tools
  - Verification & Testing

- **`setup_postgresql.sh`** - Quick setup script
  - Installs PostgreSQL
  - Creates database and user
  - Configures authentication
  - Tests connection

- **`pg_viewer.py`** - Gradio web interface
  - Browse tables with pagination
  - Search within tables
  - Export data (CSV, Excel, JSON)
  - Automatic public URL generation

### Backup Directory

The `backup_original/` directory contains all the original scripts that were consolidated:

- Multiple setup scripts (Docker, WSL, interactive versions)
- Various viewers (Flask, Gradio, terminal-based)
- Migration and sync tools
- Verification scripts
- Google Sheets sync scripts

## 🔧 Configuration

Default PostgreSQL configuration:
- **Host**: localhost
- **Port**: 5432
- **Database**: autotrainx
- **User**: autotrainx
- **Password**: 1234

You can override these with environment variables:
```bash
export AUTOTRAINX_DB_HOST=your_host
export AUTOTRAINX_DB_PORT=your_port
export AUTOTRAINX_DB_NAME=your_database
export AUTOTRAINX_DB_USER=your_user
export AUTOTRAINX_DB_PASSWORD=your_password
```

## 📋 Features

### PostgreSQL Manager (`postgresql_manager.py`)

**Interactive menu system with:**
- 🚀 **Setup & Installation**
  - Install PostgreSQL
  - Create database & user
  - Fix authentication issues
  - Full automated setup

- 🔍 **Database Viewer**
  - Terminal table viewer
  - Web viewers (Gradio/Flask)
  - Export to HTML

- 🔧 **Utilities & Tools**
  - Migrate from SQLite
  - Sync to SQLite
  - Quick psql connection
  - Database statistics
  - Cleanup & maintenance

- 📊 **Verification & Testing**
  - Connection testing
  - Table structure verification
  - Integration tests
  - Health reports

### Web Viewer (`pg_viewer.py`)

**Gradio-based interface with:**
- Table browsing with pagination
- Column sorting
- Full-text search
- Export functionality (CSV, Excel, JSON)
- Automatic public URL for sharing

## 🔄 Migration

To migrate from SQLite to PostgreSQL:

1. Use the PostgreSQL Manager:
   ```bash
   python postgresql_manager.py
   # Select: Utilities & Tools → Migrate from SQLite
   ```

2. Or run directly:
   ```bash
   python backup_original/migrate_simple.py /path/to/autotrainx.db
   ```

## 🧪 Testing

Test your PostgreSQL setup:
```bash
python postgresql_manager.py
# Select: Verification & Testing → Run Integration Tests
```

## 🆘 Troubleshooting

### Connection Issues
1. Run the manager and select "Fix Authentication Issues"
2. Check PostgreSQL service: `sudo systemctl status postgresql`
3. Verify pg_hba.conf settings

### Permission Errors
1. Ensure the database user has proper privileges
2. Run: `sudo -u postgres psql -c "GRANT ALL ON DATABASE autotrainx TO autotrainx;"`

### Port Already in Use
For the web viewer, the port is automatically assigned by Gradio. If you need a specific port:
```python
app.launch(share=True, server_port=7860)
```

## 📝 Notes

- The unified scripts consolidate functionality from ~24 original scripts
- All original scripts are preserved in `backup_original/`
- The new structure provides a cleaner, more maintainable codebase
- Compatible with Docker, WSL, and standard Linux environments
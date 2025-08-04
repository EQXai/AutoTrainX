# AutoTrainX Installation Guide

This guide provides step-by-step instructions for new users to install and configure AutoTrainX with all its features including PostgreSQL database and Google Sheets synchronization.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Installation Steps](#detailed-installation-steps)
4. [Configuration](#configuration)
5. [Verification](#verification)
6. [Starting Services](#starting-services)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

- **Operating System**: Ubuntu 20.04+ / Debian 10+ / WSL2
- **Python**: 3.8 or higher
- **Git**: For cloning the repository
- **sudo**: Administrative privileges for installing system packages
- **Internet Connection**: For downloading dependencies

## Quick Start

For experienced users who want to get up and running quickly:

```bash
# Clone and setup
git clone https://github.com/your-username/AutoTrainX.git
cd AutoTrainX
./setup.sh                    # Select appropriate profile

# Database setup
cd database_utils
python postgresql_manager.py   # Select: Full Setup
cd ..

# Google Sheets setup
python setup_google_sheets.py  # Provide credentials

# Start sync daemon
python sheets_sync_manager.py  # Daemon Control → Start Background

# Ready to use!
python main.py --help
```

## Detailed Installation Steps

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/AutoTrainX.git
cd AutoTrainX
```

### Step 2: Run the Main Setup Script

Execute the setup script and choose the appropriate installation profile:

```bash
./setup.sh
```

You will see the following options:

| Profile | Description | Use Case |
|---------|-------------|----------|
| **Development** | Full development environment with all tools | Local development |
| **Docker** | Optimized for Docker containers | Container deployment |
| **WSL** | Windows Subsystem for Linux optimized | Windows users |
| **Linux** | Standard Linux installation | Production servers |
| **Minimal** | Core components only | Limited environments |

Select the profile that matches your environment by entering the corresponding number.

### Step 3: PostgreSQL Database Setup

AutoTrainX uses PostgreSQL as its primary database. You have two options:

#### Option A: Quick Setup (Recommended for beginners)
```bash
cd database_utils
./setup_postgresql.sh
cd ..
```

This script will:
- Install PostgreSQL (if not already installed)
- Create the `autotrainx` database
- Create the `autotrainx` user with password `1234`
- Configure authentication

#### Option B: Interactive Setup (Recommended for advanced users)
```bash
cd database_utils
python postgresql_manager.py
cd ..
```

In the interactive menu:
1. Select **🚀 Setup & Installation**
2. Choose **🔄 Full Setup (Install + Configure)**
3. Follow the prompts

### Step 4: Google Sheets Integration Setup

AutoTrainX can synchronize training data with Google Sheets for easy monitoring and sharing.

#### 4.1 Prepare Google Cloud Credentials

Before running the setup:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Google Sheets API"
   - Click "Enable"
4. Create credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "Service Account"
   - Fill in the service account details
   - Download the JSON key file

#### 4.2 Run the Setup Script

```bash
python setup_google_sheets.py
```

You will be prompted for:
- **Path to credentials JSON file**: The file you downloaded from Google Cloud
- **Google Sheets ID**: Found in your sheet's URL: `https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit`

#### 4.3 Share Your Google Sheet

**Important**: Share your Google Sheet with the service account email found in your credentials JSON file.

### Step 5: Complete Configuration via Interactive Menu

Use the main menu system for final configuration:

```bash
python menu.py
```

Navigate to:
1. **⚙️ Configuration Management**
2. **📊 Google Sheets Sync**
3. Complete the following:
   - ✅ **Enable/Disable Sync** (Enable it)
   - 📊 **Test Connection** (Verify it works)

### Step 6: Start the Synchronization Daemon

```bash
python sheets_sync_manager.py
```

In the interactive menu:
1. Select **🚀 Daemon Control**
2. Choose **🚀 Start Daemon (Background)**

The daemon will now run in the background, automatically syncing your database with Google Sheets.

## Configuration

### Configuration Files

After installation, the following configuration files will be created:

| File | Purpose |
|------|---------|
| `settings/config.json` | Main configuration file |
| `settings/google_credentials.json` | Google Sheets API credentials |
| `settings/.env` | Environment variables (optional) |
| `logs/sheets_sync_daemon.log` | Sync daemon logs |

### Database Configuration

Default PostgreSQL settings:
- **Host**: localhost
- **Port**: 5432
- **Database**: autotrainx
- **User**: autotrainx
- **Password**: 1234

To use custom settings, set environment variables:
```bash
export AUTOTRAINX_DB_HOST=your_host
export AUTOTRAINX_DB_PORT=your_port
export AUTOTRAINX_DB_NAME=your_database
export AUTOTRAINX_DB_USER=your_user
export AUTOTRAINX_DB_PASSWORD=your_password
```

## Verification

### Verify Installation

Run the verification checklist:

```bash
python menu.py
```

Check the following:
1. **Information & Status** → **System Status**
   - Should show all components as "Active"
2. **Information & Status** → **Database Statistics**
   - Should connect and show table information

### Test Database Connection

```bash
cd database_utils
python postgresql_manager.py
# Select: Verification & Testing → Test Database Connection
```

### Test Google Sheets Sync

```bash
python sheets_sync_manager.py
# Select: Testing & Diagnostics → Test Google Sheets Connection
```

## Starting Services

### For Training Operations

```bash
# View available commands
python main.py --help

# Start a training job
python main.py single --dataset /path/to/images --name my_training
```

### For Development (API + Frontend)

```bash
# Start both API and frontend servers
./start_dev.sh
```

Access:
- API: http://localhost:8000
- Frontend: http://localhost:3000

### For API Only

```bash
# Start just the API server
python api_server.py
```

### View Database

```bash
# Terminal viewer
cd database_utils
python postgresql_manager.py
# Select: Database Viewer → View Tables

# Web viewer with public URL
python pg_viewer.py
```

## Troubleshooting

### PostgreSQL Connection Issues

If you get connection errors:

1. Check PostgreSQL service:
   ```bash
   sudo systemctl status postgresql
   ```

2. Fix authentication:
   ```bash
   cd database_utils
   python postgresql_manager.py
   # Select: Setup & Installation → Fix Authentication Issues
   ```

### Google Sheets Sync Issues

1. Verify API is enabled in Google Cloud Console
2. Check credentials file permissions
3. Ensure sheet is shared with service account email
4. Check logs:
   ```bash
   python sheets_sync_manager.py
   # Select: Monitoring & Logs → View Recent Logs
   ```

### Permission Errors

If you encounter permission errors:
```bash
# Fix file permissions
chmod +x setup.sh
chmod +x database_utils/*.sh
chmod +x *.py
```

### Port Already in Use

If ports 8000 or 3000 are in use:
```bash
# Kill processes using the ports
sudo lsof -ti:8000 | xargs kill -9
sudo lsof -ti:3000 | xargs kill -9
```

## Next Steps

After successful installation:

1. **Read the Documentation**:
   - `docs/README.md` - Project overview
   - `docs/API.md` - API documentation
   - `docs/TRAINING.md` - Training guide

2. **Explore the Features**:
   - Try different training presets
   - Experiment with the web interface
   - Monitor training progress in Google Sheets

3. **Join the Community**:
   - Report issues on GitHub
   - Share your results
   - Contribute improvements

## Support

If you encounter issues not covered in this guide:

1. Check existing issues on GitHub
2. Review logs in the `logs/` directory
3. Run diagnostic tools:
   ```bash
   python sheets_sync_manager.py
   # Select: Testing & Diagnostics → Generate Diagnostic Report
   ```

Happy training with AutoTrainX! 🚀
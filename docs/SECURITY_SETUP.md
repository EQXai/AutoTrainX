# 🔒 AutoTrainX Security Configuration Guide

## Overview

This guide explains how to securely configure AutoTrainX to protect sensitive information like database passwords and API credentials.

## ⚠️ Security Best Practices

1. **NEVER commit credentials to version control**
2. **Use strong, unique passwords** for each environment
3. **Rotate secrets regularly** (at least every 90 days)
4. **Limit access** to production credentials
5. **Use environment variables** instead of hardcoded values

## Quick Start

### 1. Run the Setup Script

```bash
python setup_secure_config.py
```

This interactive script will help you:
- Generate secure passwords
- Configure database connections
- Set up Google Cloud credentials
- Configure API security

### 2. Manual Configuration

If you prefer manual setup, copy the example file:

```bash
cp .env.example .env
```

Then edit `.env` and replace all placeholder values:

#### Database Configuration
```bash
# PostgreSQL (recommended for production)
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=autotrainx
DATABASE_USER=autotrainx
DATABASE_PASSWORD=<STRONG_PASSWORD_HERE>  # Generate with: openssl rand -base64 32

# Or SQLite (development only)
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///./DB/autotrainx.db
```

#### Google Cloud Credentials

**Option 1: Environment Variables (Recommended)**
```bash
GOOGLE_SERVICE_ACCOUNT_EMAIL=your-service@project.iam.gserviceaccount.com
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
```

**Option 2: Credential File Path**
```bash
GOOGLE_APPLICATION_CREDENTIALS=/secure/path/to/credentials.json
```

#### API Security
```bash
# Generate secure keys with: python -c "import secrets; print(secrets.token_hex(32))"
API_SECRET_KEY=<64_CHARACTER_HEX_STRING>
JWT_SECRET_KEY=<64_CHARACTER_HEX_STRING>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### CORS Configuration
```bash
# Production: specify exact domains
CORS_ALLOWED_ORIGINS=https://your-app.com,https://api.your-app.com

# Development: can use * (but change for production!)
CORS_ALLOWED_ORIGINS=*
```

## Setting Up PostgreSQL

After configuring your `.env` file:

1. **Create the database and user:**
```sql
sudo -u postgres psql

CREATE USER autotrainx WITH PASSWORD 'your_secure_password_here';
CREATE DATABASE autotrainx OWNER autotrainx;
GRANT ALL PRIVILEGES ON DATABASE autotrainx TO autotrainx;
\q
```

2. **Test the connection:**
```bash
psql -U autotrainx -d autotrainx -h localhost
```

## Google Sheets Integration

### Creating a Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable Google Sheets API
4. Create a service account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Download the JSON key file

### Secure Storage Options

**Option 1: Environment Variables (Most Secure)**
- Extract values from JSON file
- Store each value as separate environment variable
- Delete the JSON file

**Option 2: Secure File Location**
- Store JSON file outside project directory
- Set restrictive permissions: `chmod 600 credentials.json`
- Reference via `GOOGLE_APPLICATION_CREDENTIALS`

### Grant Spreadsheet Access
Share your Google Sheet with the service account email:
1. Open your Google Sheet
2. Click "Share"
3. Add the service account email (ends with `@*.iam.gserviceaccount.com`)
4. Grant "Editor" access

## Validating Configuration

Run the validation script:
```python
from src.config.secure_config import secure_config

# Validate configuration
if secure_config.validate_configuration():
    print("✅ Configuration is secure")
else:
    print("❌ Security issues detected - check logs")
```

## Production Deployment

### 1. Environment Variables

For production, use your platform's secret management:

**Docker/Kubernetes:**
```yaml
env:
  - name: DATABASE_PASSWORD
    valueFrom:
      secretKeyRef:
        name: autotrainx-secrets
        key: db-password
```

**AWS:**
- Use AWS Secrets Manager or Parameter Store
- Reference via IAM roles

**Heroku:**
```bash
heroku config:set DATABASE_PASSWORD=your_secure_password
```

### 2. File Permissions

Ensure proper permissions:
```bash
# Restrict .env file access
chmod 600 .env

# Restrict credentials files
chmod 600 /path/to/credentials.json
```

### 3. Monitoring

Monitor for:
- Failed authentication attempts
- Unusual database queries
- API rate limit violations

## Troubleshooting

### Common Issues

**"Database connection failed"**
- Check DATABASE_PASSWORD is set correctly
- Verify PostgreSQL is running
- Check user permissions

**"Google credentials not found"**
- Ensure GOOGLE_APPLICATION_CREDENTIALS path is correct
- Or verify all individual Google env vars are set
- Check file permissions

**"CORS error in browser"**
- Update CORS_ALLOWED_ORIGINS for production
- Include the actual domain making requests

### Security Checklist

- [ ] Generated strong passwords (32+ characters)
- [ ] Removed all hardcoded credentials from code
- [ ] Added `.env` to `.gitignore`
- [ ] Deleted `settings/google_credentials.json`
- [ ] Set appropriate file permissions
- [ ] Configured CORS for specific domains
- [ ] Enabled HTTPS in production
- [ ] Set up secret rotation reminders

## Getting Help

If you encounter security issues:
1. Check logs for detailed error messages
2. Ensure all environment variables are set
3. Verify file permissions and paths
4. Contact the security team for sensitive issues

Remember: **Security is everyone's responsibility!**
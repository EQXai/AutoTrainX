#!/bin/bash
# Install Google Sheets sync dependencies

echo "Installing Google Sheets API dependencies..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies
pip install google-api-python-client>=2.100.0
pip install google-auth>=2.20.0
pip install google-auth-oauthlib>=1.0.0
pip install google-auth-httplib2>=0.1.0

echo "✅ Dependencies installed successfully!"
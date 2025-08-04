#!/bin/bash
# Start the AutoTrainX API server

# Get the script directory and parent directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PARENT_DIR"

# Load environment variables from settings/.env if it exists
if [ -f settings/.env ]; then
    echo "Loading environment from settings/.env file..."
    export $(grep -v '^#' settings/.env | xargs)
fi

# Also ensure PostgreSQL variables are set
export DATABASE_TYPE=${DATABASE_TYPE:-postgresql}
export AUTOTRAINX_DB_TYPE=${AUTOTRAINX_DB_TYPE:-postgresql}
export AUTOTRAINX_DB_HOST=${AUTOTRAINX_DB_HOST:-localhost}
export AUTOTRAINX_DB_PORT=${AUTOTRAINX_DB_PORT:-5432}
export AUTOTRAINX_DB_NAME=${AUTOTRAINX_DB_NAME:-autotrainx}
export AUTOTRAINX_DB_USER=${AUTOTRAINX_DB_USER:-autotrainx}
export AUTOTRAINX_DB_PASSWORD=${AUTOTRAINX_DB_PASSWORD:-1234}

echo "Starting AutoTrainX API server..."
echo "Database type: $DATABASE_TYPE"
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
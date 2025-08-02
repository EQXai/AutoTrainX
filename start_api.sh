#!/bin/bash
# Start the AutoTrainX API server

cd /home/eqx/AutoTrainX

# Load environment variables from .env if it exists
if [ -f .env ]; then
    echo "Loading environment from .env file..."
    export $(grep -v '^#' .env | xargs)
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
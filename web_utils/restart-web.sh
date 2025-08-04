#!/bin/bash

# Get the script directory and parent directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Stopping any existing Next.js processes..."
pkill -f "next dev" || true
pkill -f "node.*next" || true

echo "Waiting for ports to be freed..."
sleep 2

echo "Clearing Next.js cache..."
cd "$PARENT_DIR/autotrainx-web"
rm -rf .next

echo "Starting Next.js development server..."
npm run dev
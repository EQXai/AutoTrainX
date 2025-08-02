#!/bin/bash

echo "Stopping any existing Next.js processes..."
pkill -f "next dev" || true
pkill -f "node.*next" || true

echo "Waiting for ports to be freed..."
sleep 2

echo "Clearing Next.js cache..."
cd /home/eqx/AutoTrainX/autotrainx-web
rm -rf .next

echo "Starting Next.js development server..."
npm run dev
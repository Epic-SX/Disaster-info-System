#!/bin/bash

# Script to restart the Disaster Info System with PM2

echo "Stopping orphaned processes..."

# Stop any running backend processes
pkill -f "python.*main.py" || echo "No backend processes found"

# Stop any running frontend processes
pkill -f "next dev" || echo "No frontend processes found"

# Wait a moment for processes to stop
sleep 2

echo "Starting applications with PM2..."
pm2 start ecosystem.config.js

echo "Checking status..."
pm2 status

echo ""
echo "Done! Use 'pm2 logs' to view logs, 'pm2 monit' to monitor, or 'pm2 stop all' to stop."


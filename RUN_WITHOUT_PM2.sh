#!/bin/bash

# Script to run Disaster Info System without PM2

echo "Stopping any existing processes..."

# Stop any running backend processes
pkill -f "python.*main.py" || echo "No backend processes found"

# Stop any running frontend processes
pkill -f "next dev" || echo "No frontend processes found"

# Wait a moment for processes to stop
sleep 2

echo "Starting backend..."
cd /home/ubuntu/Disaster-info-System/backend
source /home/ubuntu/Disaster-info-System/venv/bin/activate
PYTHONPATH=/home/ubuntu/Disaster-info-System/backend nohup python main.py > /home/ubuntu/Disaster-info-System/logs/backend-manual.log 2>&1 &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

echo "Starting frontend..."
cd /home/ubuntu/Disaster-info-System/frontend
nohup npm run dev > /home/ubuntu/Disaster-info-System/logs/frontend-manual.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"

echo ""
echo "Applications started!"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "To stop:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "To view logs:"
echo "  tail -f /home/ubuntu/Disaster-info-System/logs/backend-manual.log"
echo "  tail -f /home/ubuntu/Disaster-info-System/logs/frontend-manual.log"


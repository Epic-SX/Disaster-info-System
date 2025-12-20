# PM2 Setup Guide for Disaster Info System

This guide will help you set up and run the Disaster Info System using PM2 process manager.

## Prerequisites

1. **Install PM2 globally** (if not already installed):
```bash
npm install -g pm2
```

2. **Ensure dependencies are installed**:
   - Backend: Python virtual environment with all dependencies installed
   - Frontend: Node.js dependencies installed (`npm install` in frontend directory)

3. **Ensure logs directory exists**:
```bash
mkdir -p /home/ubuntu/Disaster-info-System/logs
```

## Quick Start

### 1. Start all applications
From the project root directory (`/home/ubuntu/Disaster-info-System`):
```bash
pm2 start ecosystem.config.js
```

### 2. Check status
```bash
pm2 status
```

### 3. View logs
```bash
# View all logs
pm2 logs

# View specific app logs
pm2 logs disaster-backend
pm2 logs disaster-frontend

# View last 100 lines
pm2 logs --lines 100
```

### 4. Stop applications
```bash
# Stop all
pm2 stop all

# Stop specific app
pm2 stop disaster-backend
pm2 stop disaster-frontend
```

### 5. Restart applications
```bash
# Restart all
pm2 restart all

# Restart specific app
pm2 restart disaster-backend
pm2 restart disaster-frontend
```

### 6. Delete applications from PM2
```bash
# Delete all
pm2 delete all

# Delete specific app
pm2 delete disaster-backend
pm2 delete disaster-frontend
```

## Advanced PM2 Commands

### Save PM2 configuration for auto-start on reboot
```bash
pm2 save
pm2 startup
```
Follow the instructions provided by `pm2 startup` to enable auto-start on system reboot.

### Monitor applications
```bash
# Real-time monitoring dashboard
pm2 monit

# Show detailed information
pm2 show disaster-backend
pm2 show disaster-frontend
```

### Reload configuration (zero-downtime restart)
```bash
pm2 reload ecosystem.config.js
```

### View process information
```bash
# List all processes
pm2 list

# Show process tree
pm2 list --tree
```

## Configuration Details

The `ecosystem.config.js` file configures two applications:

1. **disaster-backend**: Python FastAPI backend server
   - Runs from `/home/ubuntu/Disaster-info-System/backend`
   - Uses Python virtual environment
   - Logs to `/home/ubuntu/Disaster-info-System/logs/backend-*.log`

2. **disaster-frontend**: Next.js frontend development server
   - Runs from `/home/ubuntu/Disaster-info-System/frontend`
   - Uses `npm run dev`
   - Logs to `/home/ubuntu/Disaster-info-System/logs/frontend-*.log`

## Troubleshooting

### Check if processes are running
```bash
pm2 status
```

### View error logs
```bash
# Backend errors
tail -f /home/ubuntu/Disaster-info-System/logs/backend-error.log

# Frontend errors
tail -f /home/ubuntu/Disaster-info-System/logs/frontend-error.log
```

### Restart failed processes
```bash
pm2 restart all
```

### Clear logs
```bash
pm2 flush
```

### Check if ports are in use
```bash
# Check backend port (usually 8000)
netstat -tulpn | grep 8000

# Check frontend port (usually 3000)
netstat -tulpn | grep 3000
```

## Production Considerations

For production, you may want to:

1. **Build the frontend** before starting:
```bash
cd frontend
npm run build
cd ..
```

2. **Update ecosystem.config.js** to use production mode:
   - Change `NODE_ENV` to `'production'`
   - Change frontend script from `npm run dev` to `npm start`
   - Consider using `watch: false` (already set)

3. **Set up PM2 to start on system boot**:
```bash
pm2 save
pm2 startup
```

## Useful PM2 Commands Summary

| Command | Description |
|---------|-------------|
| `pm2 start ecosystem.config.js` | Start all apps |
| `pm2 stop all` | Stop all apps |
| `pm2 restart all` | Restart all apps |
| `pm2 delete all` | Remove all apps from PM2 |
| `pm2 status` | Show status of all apps |
| `pm2 logs` | Show logs from all apps |
| `pm2 monit` | Open monitoring dashboard |
| `pm2 save` | Save current process list |
| `pm2 startup` | Generate startup script |
| `pm2 flush` | Clear all logs |




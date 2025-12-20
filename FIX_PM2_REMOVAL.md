# Fix Guide: After Removing PM2

If you removed PM2 from managing your processes, here are your options:

## Current Situation

- **PM2**: Still installed but not managing any processes
- **Backend**: Running as orphaned process (PID 235373)
- **Frontend**: Not running

## Option 1: Use PM2 Again (Recommended)

PM2 provides process management, auto-restart, logging, and monitoring.

### Quick Fix:
```bash
./RESTART_WITH_PM2.sh
```

### Manual Steps:
```bash
# 1. Stop orphaned processes
pkill -f "python.*main.py"
pkill -f "next dev"

# 2. Start with PM2
pm2 start ecosystem.config.js

# 3. Check status
pm2 status

# 4. View logs
pm2 logs
```

### Useful PM2 Commands:
- `pm2 status` - Check running processes
- `pm2 logs` - View all logs
- `pm2 logs disaster-backend` - View backend logs only
- `pm2 logs disaster-frontend` - View frontend logs only
- `pm2 stop all` - Stop all processes
- `pm2 restart all` - Restart all processes
- `pm2 delete all` - Remove from PM2 (but processes keep running)
- `pm2 monit` - Open monitoring dashboard

## Option 2: Run Without PM2

If you prefer not to use PM2, you can run the applications manually.

### Quick Fix:
```bash
./RUN_WITHOUT_PM2.sh
```

### Manual Steps:

#### Start Backend:
```bash
cd /home/ubuntu/Disaster-info-System/backend
source /home/ubuntu/Disaster-info-System/venv/bin/activate
PYTHONPATH=/home/ubuntu/Disaster-info-System/backend python main.py
```

#### Start Frontend (in another terminal):
```bash
cd /home/ubuntu/Disaster-info-System/frontend
npm run dev
```

#### Or Run in Background:
```bash
# Backend
cd /home/ubuntu/Disaster-info-System/backend
source /home/ubuntu/Disaster-info-System/venv/bin/activate
nohup python main.py > ../logs/backend-manual.log 2>&1 &

# Frontend
cd /home/ubuntu/Disaster-info-System/frontend
nohup npm run dev > ../logs/frontend-manual.log 2>&1 &
```

## Clean Up Orphaned Processes

If you have orphaned processes running:

```bash
# Find processes
ps aux | grep -E "(python.*main.py|next dev|npm.*dev)"

# Kill backend
pkill -f "python.*main.py"

# Kill frontend
pkill -f "next dev"
pkill -f "npm.*dev"
```

## Check What's Running

```bash
# Check ports
lsof -i :8000  # Backend port
lsof -i :3000  # Frontend port

# Check processes
ps aux | grep -E "(python|node|npm)" | grep -v grep
```

## Recommendation

**Use PM2** because it provides:
- ✅ Automatic restart on crashes
- ✅ Process monitoring
- ✅ Centralized logging
- ✅ Easy start/stop/restart
- ✅ Auto-start on system reboot (with `pm2 startup`)

## Next Steps

1. **If using PM2**: Run `./RESTART_WITH_PM2.sh`
2. **If not using PM2**: Run `./RUN_WITHOUT_PM2.sh`
3. **Verify**: Check that both backend (port 8000) and frontend (port 3000) are accessible


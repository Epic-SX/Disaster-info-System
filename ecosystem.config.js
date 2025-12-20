module.exports = {
  apps: [
    {
      name: 'disaster-backend',
      script: '/home/ubuntu/Disaster-info-System/venv/bin/python',
      args: 'main.py',
      cwd: '/home/ubuntu/Disaster-info-System/backend',
      env: {
        NODE_ENV: 'development',
        PYTHONPATH: '/home/ubuntu/Disaster-info-System/backend'
      },
      log_file: '/home/ubuntu/Disaster-info-System/logs/backend-combined.log',
      out_file: '/home/ubuntu/Disaster-info-System/logs/backend-out.log',
      error_file: '/home/ubuntu/Disaster-info-System/logs/backend-error.log',
      time: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 4000,
      watch: false,
      instances: 1,
      exec_mode: 'fork'
    },
    {
      name: 'disaster-frontend',
      script: 'npm',
      args: 'run dev',
      cwd: '/home/ubuntu/Disaster-info-System/frontend',
      env: {
        NODE_ENV: 'development'
      },
      log_file: '/home/ubuntu/Disaster-info-System/logs/frontend-combined.log',
      out_file: '/home/ubuntu/Disaster-info-System/logs/frontend-out.log',
      error_file: '/home/ubuntu/Disaster-info-System/logs/frontend-error.log',
      time: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 4000,
      watch: false,
      instances: 1,
      exec_mode: 'fork'
    }
  ]
}; 
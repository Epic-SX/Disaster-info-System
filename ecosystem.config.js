module.exports = {
  apps: [
    {
      name: 'disaster-backend',
      script: '/home/ubuntu/Disaster-info-System/venv/bin/python',
      args: 'main.py',
      cwd: './backend',
      env: {
        NODE_ENV: 'development',
        PYTHONPATH: './backend'
      },
      log_file: './logs/backend-combined.log',
      out_file: './logs/backend-out.log',
      error_file: './logs/backend-error.log',
      time: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 4000
    },
    {
      name: 'disaster-frontend',
      script: 'npm',
      args: 'run dev',
      cwd: './frontend',
      env: {
        NODE_ENV: 'development'
      },
      log_file: './logs/frontend-combined.log',
      out_file: './logs/frontend-out.log',
      error_file: './logs/frontend-error.log',
      time: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 4000
    }
  ]
}; 
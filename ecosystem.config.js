module.exports = {
  apps: [
    {
      name: "file-watcher",
      script: "src/watchers/filesystem_watcher.py",
      interpreter: "D:\\ai-employee-project\\.venv\\Scripts\\python.exe",
      cwd: "D:\\ai-employee-project",
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 2000,
    },
    {
      name: "orchestrator",
      script: "src/orchestrator.py",
      interpreter: "D:\\ai-employee-project\\.venv\\Scripts\\python.exe",
      cwd: "D:\\ai-employee-project",
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 2000,
    },
    {
      name: "news-watcher",
      script: "src/watchers/news_watcher.py",
      interpreter: "D:\\ai-employee-project\\.venv\\Scripts\\python.exe",
      cwd: "D:\\ai-employee-project",
      cron_restart: "0 8 * * *",
      autorestart: false,
      watch: false,
    },
    // Gmail watcher — polls every 2 min via its own internal loop
    {
      name: "gmail-watcher",
      script: "src/watchers/gmail_watcher.py",
      interpreter: "D:\\ai-employee-project\\.venv\\Scripts\\python.exe",
      cwd: "D:\\ai-employee-project",
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 2000,
    },
    // AI scheduler — runs every 30 min to trigger reasoning tasks
    // Note: WhatsApp watcher is NOT here — start it manually with --first-run for QR scan
    {
      name: "ai-scheduler",
      script: "src/scheduler.py",
      interpreter: "D:\\ai-employee-project\\.venv\\Scripts\\python.exe",
      cwd: "D:\\ai-employee-project",
      cron_restart: "*/30 * * * *",
      autorestart: false,
      watch: false,
    },
  ],
};

"""Gunicorn configuration for libre-convert-api."""
import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('API_PORT', '28001')}"
backlog = 2048

# Worker processes
_workers = os.getenv("API_WORKERS", "auto")
if _workers == "auto":
    workers = multiprocessing.cpu_count()
else:
    workers = int(_workers)

worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeout
timeout = int(os.getenv("API_TIMEOUT", "300"))
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
access_log_format = '{"timestamp":"%(t)s","client":"%(h)s","method":"%(m)s","path":"%(U)s","status":"%(s)s","size":"%(B)s","time":"%(D)s"}'

# Process naming
proc_name = "libre-convert-api"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (disabled by default, use reverse proxy for TLS)
keyfile = None
certfile = None

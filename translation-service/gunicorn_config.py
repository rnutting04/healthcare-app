# --- Gunicorn Settings ---
bind = "0.0.0.0:8008"
workers = 3
worker_class = "uvicorn.workers.UvicornWorker"
loglevel = "info"
# --- Gunicorn Settings ---
bind = "0.0.0.0:8010"
workers = 3
worker_class = "uvicorn.workers.UvicornWorker"
loglevel = "info"
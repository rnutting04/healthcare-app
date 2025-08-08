#!/bin/sh

echo "Starting Gunicorn server with config file..."
exec gunicorn -c gunicorn_config.py main:app
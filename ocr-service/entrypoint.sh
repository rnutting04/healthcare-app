#!/bin/bash

echo "Starting OCR Service..."

# Set Django settings module
export DJANGO_SETTINGS_MODULE=ocr_service.settings

# Wait for Redis
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis is ready!"

# Run migrations (even though we don't use database, Django needs this)
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Daphne server for WebSocket support
# The OCR processing thread will be started when the first request comes in
echo "Starting Daphne server..."
exec daphne -b 0.0.0.0 -p 8008 ocr_service.asgi:application
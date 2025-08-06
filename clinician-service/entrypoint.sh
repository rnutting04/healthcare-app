#!/bin/bash

# Exit on error
set -e

echo "Starting Clinician Service..."

# Run migrations (no-op since we use in-memory SQLite)
echo "Running migrations..."
python manage.py migrate --noinput || true

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || true

# Start the application
echo "Starting Gunicorn..."
exec "$@"
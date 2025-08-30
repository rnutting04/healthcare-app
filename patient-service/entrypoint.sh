#!/bin/sh

echo "Waiting for postgres..."

while ! nc -z postgres 5432; do
  sleep 0.1
done

echo "PostgreSQL started"

# Wait a bit to ensure auth-service has run its migrations first
echo "Waiting for auth-service to initialize..."
sleep 10

# No migrations needed for patient service as it doesn't have local models
echo "Patient service ready (no migrations needed)"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the server
echo "Starting server..."
exec "$@"
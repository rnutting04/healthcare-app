#!/bin/sh

echo "Waiting for postgres..."

while ! nc -z postgres 5432; do
  sleep 0.1
done

echo "PostgreSQL started"

# Wait a bit to ensure auth-service has run its migrations first
echo "Waiting for auth-service to initialize..."
sleep 10

# Run only app-specific migrations
echo "Running database migrations..."
python manage.py migrate data_management --noinput || true

# Start the server
echo "Starting server..."
exec "$@"
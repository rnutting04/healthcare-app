#!/bin/sh

echo "Waiting for postgres..."

while ! nc -z postgres 5432; do
  sleep 0.1
done

echo "PostgreSQL started"

# Wait a bit to ensure auth-service has run its migrations first
echo "Waiting for auth-service to initialize..."
sleep 10

# Run migrations in the correct order
echo "Running database migrations..."
# First ensure data_management initial migration is applied
python manage.py migrate data_management 0001_initial --fake-initial --noinput || true
# Then run all remaining migrations
python manage.py migrate --noinput || true

# Start the server
echo "Starting server..."
exec "$@"
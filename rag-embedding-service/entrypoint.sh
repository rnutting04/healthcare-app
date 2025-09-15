#!/bin/sh

echo "Waiting for database service..."

while ! nc -z database-service 8004; do
  sleep 0.1
done

echo "Database service is ready"

# Wait for Redis
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.1
done

echo "Redis is ready"

# Run Django migrations (though this service doesn't have its own database)
echo "Running migrations..."
python manage.py migrate --noinput || true

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || true

# Start the server
echo "Starting RAG embedding service..."
exec "$@"
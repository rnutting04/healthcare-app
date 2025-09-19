#!/bin/sh

set -e

echo "Waiting for postgres..."

while ! nc -z postgres 5432; do
  sleep 0.1
done

echo "PostgreSQL started"

echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis is ready!"

# Wait a bit to ensure auth-service has run its migrations first
echo "Waiting for auth-service to initialize..."
sleep 10

export DJANGO_SETTINGS_MODULE=patient_service.settings

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Daphne ASGI server..."
exec daphne -b 0.0.0.0 -p 8002 patient_service.asgi:application

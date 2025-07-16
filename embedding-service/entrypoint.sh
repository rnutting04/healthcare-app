#!/bin/bash

echo "Starting Embedding Service..."

# Wait for database service to be ready
echo "Waiting for database service..."
while ! nc -z database-service 8004; do
  sleep 1
done
echo "Database service is ready!"

# Wait for auth service to be ready
echo "Waiting for auth service..."
while ! nc -z auth-service 8001; do
  sleep 1
done
echo "Auth service is ready!"

# Run Django migrations (if any local ones exist)
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the Django development server
echo "Starting Django server..."
python manage.py runserver 0.0.0.0:8007
#!/bin/sh

echo "Waiting for postgres..."

while ! nc -z postgres 5432; do
  sleep 0.1
done

echo "PostgreSQL started"

# Wait a bit to ensure auth-service has run its migrations first
echo "Waiting for auth-service to initialize..."
sleep 10

# Enable PGVector extension
echo "Enabling PGVector extension..."
python manage.py enable_pgvector

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Create admin user if it doesn't exist
echo "Creating admin user..."
python manage.py create_admin_user

# Import cancer types from JSON file
echo "Importing cancer types..."
python manage.py import_cancer_types

echo "Importing suggestions..."
python manage.py import_suggestions

# Start the server
echo "Starting server..."
exec "$@"

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variable for Django settings
ENV DJANGO_SETTINGS_MODULE=settings

# Create static and media directories
RUN mkdir -p static media

# Collect static files
RUN python manage.py collectstatic --noinput || true

EXPOSE 8003

CMD ["gunicorn", "--bind", "0.0.0.0:8003", "--workers", "4", "--threads", "2", "wsgi:application"]
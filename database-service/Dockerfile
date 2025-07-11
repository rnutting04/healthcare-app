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

# Install netcat and dos2unix for database connectivity check and line ending conversion
RUN apt-get update && apt-get install -y netcat-openbsd dos2unix && rm -rf /var/lib/apt/lists/*

# Copy entrypoint script and convert line endings
COPY --chmod=755 entrypoint.sh /entrypoint.sh
RUN dos2unix /entrypoint.sh

EXPOSE 8004

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8004", "--workers", "4", "--threads", "2", "wsgi:application"]
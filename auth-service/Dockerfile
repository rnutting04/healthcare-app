FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Node.js for Tailwind
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    netcat-traditional \
    dos2unix \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories first
RUN mkdir -p static/css

# Copy package.json and Tailwind config files
COPY package.json tailwind.config.js ./
COPY static/css/input.css static/css/

# Debug: Show npm version
RUN node --version && npm --version

# Install Node dependencies with verbose output
RUN npm install --verbose

# Copy application code
COPY . .

# Set environment variable for Django settings
ENV DJANGO_SETTINGS_MODULE=settings

# Debug: List files to ensure everything is copied
RUN ls -la && ls -la static/css/

# Build Tailwind CSS with full error output
RUN npx tailwindcss -i ./static/css/input.css -o ./static/css/main.css --minify || (echo "Tailwind build failed" && exit 1)

# Verify the CSS was built
RUN test -f static/css/main.css || (echo "main.css not found after build" && exit 1)
RUN ls -la static/css/

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Copy entrypoint script and convert line endings
COPY entrypoint.sh entrypoint.sh
RUN dos2unix entrypoint.sh && chmod +x entrypoint.sh

EXPOSE 8001

ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8001", "--workers", "4", "--threads", "2", "wsgi:application"]
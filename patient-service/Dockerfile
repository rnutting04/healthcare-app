FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Node.js for Tailwind
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy package.json first
COPY package.json ./

# Install Node dependencies (this must happen before copying other files)
RUN npm install

# Now copy the rest of the application
COPY . .

# Build Tailwind CSS
RUN npx tailwindcss -i ./static/css/input.css -o ./static/css/main.css --minify

# Verify the CSS was built
RUN ls -la static/css/ && test -f static/css/main.css

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Install netcat and dos2unix for database connectivity check and line ending conversion
RUN apt-get update && apt-get install -y netcat-openbsd dos2unix && rm -rf /var/lib/apt/lists/*

# Copy entrypoint script and convert line endings
COPY --chmod=755 entrypoint.sh /entrypoint.sh
RUN dos2unix /entrypoint.sh

EXPOSE 8002

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8002", "--workers", "4", "--threads", "2", "wsgi:application"]
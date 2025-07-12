FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update
RUN apt-get install -y gcc
RUN apt-get install -y postgresql-client
RUN apt-get install -y curl

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
RUN apt-get install -y nodejs

# Clean up apt cache
RUN rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy package.json first
COPY package.json ./

# Install Node dependencies
RUN npm install

# Now copy the rest of the application
COPY . .

# Build Tailwind CSS
RUN npx tailwindcss -i ./static/css/input.css -o ./static/css/main.css --minify

# Verify the CSS was built
RUN ls -la static/css/
RUN test -f static/css/main.css

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Install netcat and dos2unix for database connectivity check
RUN apt-get update
RUN apt-get install -y netcat-openbsd
RUN apt-get install -y dos2unix
RUN rm -rf /var/lib/apt/lists/*

# Copy entrypoint script and convert line endings
COPY --chmod=755 entrypoint.sh /entrypoint.sh
RUN dos2unix /entrypoint.sh

EXPOSE 8005

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8005", "--workers", "4", "--threads", "2", "wsgi:application"]
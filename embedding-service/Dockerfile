FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    netcat-traditional \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Create media directory for temporary file storage
RUN mkdir -p /app/media/temp_files

# Expose port
EXPOSE 8007

# Copy entrypoint script and convert line endings
COPY --chmod=755 entrypoint.sh /entrypoint.sh
RUN dos2unix /entrypoint.sh

# Run the entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
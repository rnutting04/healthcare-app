FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    wget \
    netcat-openbsd \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create media directory
RUN mkdir -p media/temp_files

# Copy entrypoint script and convert line endings
COPY --chmod=755 entrypoint.sh /entrypoint.sh
RUN dos2unix /entrypoint.sh

# Expose port
EXPOSE 8008

# Run entrypoint
CMD ["/entrypoint.sh"]
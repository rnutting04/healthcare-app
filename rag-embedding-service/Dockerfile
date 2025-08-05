FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    build-essential \
    dos2unix \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/media/temp_files
RUN mkdir -p /app/static

# Copy entrypoint script and convert line endings
COPY --chmod=755 entrypoint.sh /entrypoint.sh
RUN dos2unix /entrypoint.sh

EXPOSE 8007

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8007"]
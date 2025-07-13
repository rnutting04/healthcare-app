FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/media/encrypted_files
RUN mkdir -p /app/static

EXPOSE 8006

CMD ["python", "manage.py", "runserver", "0.0.0.0:8006"]
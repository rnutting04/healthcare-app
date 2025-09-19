# Translation Service

A high-performance, asynchronous translation microservice for the Healthcare App, powered by local machine learning models.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Data Flow](#data-flow)
- [API Endpoints](#api-endpoints)
- [Security Implementation](#security-implementation)
- [Setup Instructions](#setup-instructions)
- [Environment Variables](#environment-variables)
- [Technical Details](#technical-details)
- [Error Handling](#error-handling)
- [Response Examples](#response-examples)

## Overview

The Translation Service is a microservice designed to provide fast and reliable text translation. It operates asynchronously, accepting translation requests and processing them in the background. This design ensures that the main healthcare application remains responsive, even when handling large volumes of text. The service leverages pre-trained models from Hugging Face for high-quality translations and uses Redis for task queuing and result caching.

## Architecture

### System Components

1.  **FastAPI Service (Gunicorn + Uvicorn)** - Main service handling API requests, job submission, and result retrieval.
2.  **Redis** - Used as a message broker for the job queue and a cache for completed results.
3.  **Background Worker Process** - A separate process that consumes jobs, performs translations, and stores results.
4.  **Hugging Face `transformers`** - The library used to download and run the translation models locally
5.  **Authentication Layer** - JWT-based authentication.

### Directory Structure

```
translation-service/
├── api/                    # API-related files
│   ├── serializers.py    # Pydantic models for request/response validation
│   └── views.py          # FastAPI router and endpoint logic
├── services/               # Core business logic
│   └── translation.py    # Worker logic, model loading, and caching functions
├── translation_service/    # Project configuration
│   └── config.py         # Central configuration and constants
├── .dockerignore           # Files to ignore in Docker context
├── Dockerfile              # Multi-stage Dockerfile for a lean production image
├── auth.py                 # Authentication dependency
├── db.py                   # Redis client initialization
├── entrypoint.sh           # Script to start the Gunicorn server
├── gunicorn_config.py      # Gunicorn server settings
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
└── worker.py               # Entry point for the background worker process
```
## Features

-   **Asynchronous Processing**: Non-blocking API for submitting translation jobs.
-   **Result Caching**: Prevents re-translating the same text using a SHA-256 hash-based key.
-   **Batch Job Processing**: Groups jobs by language to translate them efficiently in batches.
-   **Duplicate Job Prevention**: Avoids queuing a new job if an identical one is already in progress.
-   **In-Memory Model Caching**: ML models are loaded once and reused to minimize latency.
-   **Scalable Worker Design**: Multi-threaded workers process jobs concurrently
-   **Multi-Language Support**: Supports French, Spanish, Chinese, Hindi, and Arabic.


## Data Flow

### Translation Submission Flow

1.  **Authentication**: Client sends JWT token in `Authorization` header.
2.  **Validation**: Service validates the token by calling the central auth service.
3.  **Cache Calculation**: A SHA-256 hash is calculated from the text and target language.
4.  **Cache Check**:
    -   Service queries Redis for an existing translation with the same hash.
    -   If a completed result is found (`200 OK` status), it is returned immediately.
5.  **Job Queuing**:
    -   If no result is found, a unique `request_id` is generated.
    -   An `in_progress` placeholder is set in the cache.
    -   The job is pushed to the Redis `translation_request_queue`.
6.  **Response**:
    -   A `202 ACCEPTED` response is returned with the `request_id`.


### Background Processing Flow

1.  **Job Consumption**: The background worker pulls a batch of jobs from the Redis queue.
2.  **Grouping**: Jobs are grouped by target language for efficient model usage.
3.  **Translation**:
    -   The appropriate ML model is loaded from the in-memory cache.
    -   Texts are translated in batches
4.  **Result Storage**:
    -   The final result overwrites the `in_progress` placeholder in the main translation cache.

### Result Retrieval Flow

1.  **Authentication**: Client sends a `GET /api/result/{request_id}` request with a valid token.
2.  **Authorization**:
    -   Client polls the result endpoint with the `request_id`.
3.  **Result Lookup**:
    -   The service retrieves the job status from the temporary result cache in Redis.
4.  **Response**:
    -   The service returns the current status (`in_progress`, `completed`, or `failed`).
    -   If the job is complete, the translated text is included.

## API Endpoints

### Submit Translation Job
```
POST /api/translate
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

Body: {"text": "Hello world", "target_language": "es"}
```

### Get Translation Result
```
GET /api/result/<request_id>
Authorization: Bearer <JWT_TOKEN>
```

### Health Check
```
GET /api/health
```

## Security Implementation

### Authentication & Authorization

1.  **JWT Token Validation**:
    ```python 
    # from auth.py
    async def verify_token(request: Request):
        # ... logic to call the central auth service ...
    ```

2.  **User Verification**:
    -   Extracts user identity from a valid JWT payload.
    -   All API operations require a valid, authenticated session.

3.  **Service-to-Service Auth**:
    -   Uses an X-Service-Token header for internal service calls.
    -   Ensures only authorized services can interact with the API.

## Setup Instructions

1.  **Worker Configuration**:
    ```bash
    # The translation service requires a separate worker process to run
    # Ensure both the 'translation-service' and 'worker' are defined in docker-compose
    ```

1.  **Environment Configuration**:
    ```bash
    cp .env.example .env 
    # Edit .env with appropriate values
    ```

2.  **Start Service**:
    ```bash
    docker-compose up translation-service translation-worker
    ```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AUTH_SERVICE_URL` | URL for the central authentication service. | `http://auth-service:8001` |
| `TRANSLATION_SERVICE_TOKEN`| Secret for service-to-service communication. | `None` |
| `REDIS_HOST` | Hostname for the Redis instance. | `redis` |
| `REDIS_PORT` | Port for the Redis instance. | `6379` |
| `NUM_WORKER_THREADS` | Number of concurrent worker threads. | `3` |
| `BATCH_SIZE` | Max number of jobs processed per batch. | `8` |

## Technical Details

### Cache Key Generation

To ensure consistency, a cache key is generated using a SHA-256 hash of the text and language.

```python
def get_translation_cache_key(text: str, lang: str):
    key_string = f"{text}:{lang}".encode('utf-8')
    key_hash = hashlib.sha256(key_string).hexdigest()
    return f"{TRANSLATION_CACHE_PREFIX}{key_hash}"
```

### Asynchronous Job Processing

1. Producer (API): The /api/translate endpoint acts as the producer, pushing jobs onto the translation_request_queue list in Redis.

2. Consumer (Worker): The background worker process continuously runs a loop that blocks and waits for new items to appear on the queue (blpop), ensuring efficient processing without constant polling.

### Batch Processing

The worker pulls multiple jobs from the queue and groups them by language. This allows the ML model to process a batch of texts in a single, highly optimized operation, dramatically improving throughput compared to one-by-one processing.

### Worker & Model Management

The worker.py script pre-loads all translation models into the main process's memory upon startup. It then spawns multiple threads, which share access to these cached models. This strategy significantly reduces translation latency by avoiding slow disk I/O and model re-initialization for every job.

## Error Handling

### Client Errors (4xx)

-   **400 Bad Request**: Invalid or missing request body parameters.
-   **401 Unauthorized**: Invalid or missing JWT or Service Token.
-   **404 Not Found**: The specified `request_id` does not exist or has expired.

### Server Errors (5xx)

-   **503 Service Unavailable**:
    -   Cannot connect to Redis.
    -   Cannot connect to the central Authentication Service.

### Error Response Format

```json
{
    "detail": "Human-readable error message"
}
```

## Response Examples

### Job Submission Success
```json
{
    "message": "Request accepted.",
    "request_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
}
```

### Immediate Cache Hit
```json
{
    "status": "completed",
    "result": "Hola Mundo",
    "from_cache": true
}
```

### Result Retrieval Response
```json
{
    "status": "completed",
    "result": "Bonjour le monde",
    "from_cache": false
}
```

## Performance Considerations
1. **Batch Tuning**: The `BATCH_SIZE` and `BATCH_TIMEOUT` variables can be tuned to balance latency and throughput.
2. **Worker Scaling**: The `NUM_WORKER_THREADS` can be increased to improve concurrent processing on multi-core systems
3. **Hardware Acceleration**: The service is currently CPU-only but could be adapted to use GPUs for significant performance gains.

## Future Enhancements

1. **Model Optimization**: For higher performance, models could be converted to a more optimized format like ONNX or be quantized.
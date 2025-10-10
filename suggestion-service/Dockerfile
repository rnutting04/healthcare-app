# ---- Runtime (CPU-only, slim) ----
FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models_cache \
    TOKENIZERS_PARALLELISM=false 

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 1) Install CPU-only Torch first (prevents pulling giant CUDA wheels)
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch

# 2) Install runtime deps (no onnx/optimum unless needed)
RUN pip install --no-cache-dir fastapi uvicorn sentence-transformers numpy pyjwt

COPY suggestion_api.py suggestions.json ./

EXPOSE 8009
CMD ["uvicorn", "suggestion_api:app", "--host", "0.0.0.0", "--port", "8009"]

# ---- Stage 1: build the React frontend ---------------------------------------
FROM node:22-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Flask API + RAG pipeline ---------------------------------------
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.hf_cache \
    ANONYMIZED_TELEMETRY=False \
    TOKENIZERS_PARALLELISM=false
WORKDIR /app

# CPU-only torch keeps the image ~1.5 GB smaller than the default CUDA build.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ app/
COPY data/ data/
COPY scripts/ scripts/
COPY --from=frontend /fe/dist frontend/dist

# Bake the models and the Chroma index into the image so the container starts
# ready to answer. Set EMBED_BACKEND=hash (build arg) for a tiny offline image.
ARG EMBED_BACKEND=sentence-transformers
ENV EMBED_BACKEND=${EMBED_BACKEND}
RUN python scripts/download_models.py && python -m app.ingest

EXPOSE 8080
# Railway injects $PORT. One worker keeps a single copy of the models in RAM;
# threads handle concurrent requests.
CMD ["sh", "-c", "PRELOAD_PIPELINE=1 exec gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 120 --access-logfile -"]

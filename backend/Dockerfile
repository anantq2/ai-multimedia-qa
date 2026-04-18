# ── Stage 1: Builder ──────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps needed to compile native wheels (faiss-cpu, whisper, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="anantq2"
LABEL description="AI-Powered Document & Multimedia Q&A — FastAPI Backend"

WORKDIR /app

# Runtime deps: ffmpeg is required by Whisper for audio/video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source code
COPY . .

# Create directories for uploads and FAISS indexes
RUN mkdir -p uploads faiss_indexes

# Expose the FastAPI port
EXPOSE 8000

# Health check — hit the /health endpoint every 30 s
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with uvicorn (0.0.0.0 so Docker can forward the port)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

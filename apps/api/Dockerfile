# ============================================================
# MEDIFLOW Backend API — Production Dockerfile (Self-Hosted)
# Multi-stage Python 3.11 + uv + RapidOCR/OpenCV/PyMuPDF
# Runs migrations automatically and executes as non-root user.
# ============================================================

FROM python:3.11-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install locked production dependencies first (maximizes Docker layer cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source and Alembic migrations
COPY mediflow ./mediflow
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

RUN uv sync --frozen --no-dev


FROM python:3.11-slim-bookworm AS runtime

# Minimal native runtime libraries required by opencv-python-headless, RapidOCR, and healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for hardened container execution
RUN groupadd --gid 1000 mediflow \
    && useradd --uid 1000 --gid mediflow --shell /bin/bash --create-home mediflow

WORKDIR /app

COPY --from=builder --chown=mediflow:mediflow /app /app

# Create persistent private document vault directory owned by mediflow
RUN mkdir -p /data/uploads && chown -R mediflow:mediflow /data/uploads

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UPLOAD_DIR=/data/uploads \
    API_HOST=0.0.0.0 \
    API_PORT=8000

USER mediflow

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=25s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# Run pending Alembic migrations automatically before starting Uvicorn
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn mediflow.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-2} --proxy-headers --forwarded-allow-ips='*'"]

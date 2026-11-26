# Multi-stage build for smaller production images.
# Stage 1: build dependencies in a disposable layer.
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install -r requirements.txt

# Stage 2: runtime image — no build tools, no compilers.
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install only runtime libraries (no build-essential).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from the builder stage.
COPY --from=builder /install /usr/local

WORKDIR /app

COPY . .
RUN chmod +x entrypoint.sh

RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]

# Multi-stage build for smaller production images.
# Stage 1: build dependencies in a disposable layer.
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip install --prefix=/install -r requirements.txt

# Stage 2: runtime image — no build tools, no compilers.
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install only runtime libraries (no build-essential). The dist-upgrade
# pulls current security patches for base-image OS packages (e.g. zlib1g)
# at build time instead of inheriting the tag's snapshot state.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq5 curl \
    && apt-get -y upgrade \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from the builder stage.
COPY --from=builder /install /usr/local

# The builder's "pip install --upgrade pip" does not carry over (only the
# /install prefix is copied), so the runtime stage inherits the base tag's
# pip. Upgrade it here explicitly: Trivy tracks the runtime pip, and the
# pip in this image had 6 open CVEs fixed across 25.3 - 26.2.0.
RUN python -m pip install --no-cache-dir --upgrade "pip>=26.2.0"

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

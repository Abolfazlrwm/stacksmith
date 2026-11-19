#!/bin/sh
# entrypoint.sh — migrate then start gunicorn.
set -e

echo "[entrypoint] running migrations"
python manage.py migrate --noinput

echo "[entrypoint] configuring telemetry"
python -c "from config.telemetry import setup_telemetry; setup_telemetry()" || echo "[entrypoint] telemetry disabled (OTEL_EXPORTER_OTLP_TRACES_ENDPOINT not set)"

echo "[entrypoint] starting gunicorn"
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile -

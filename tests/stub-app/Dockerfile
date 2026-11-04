# CI stub image: same runtime contract as the docubot app image (gunicorn on
# 0.0.0.0:8000, POSTGRES_* + REDIS_URL env, celery app) with none of the
# docubot specifics. Used by the smoke and drill jobs.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "stub.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "30", "--access-logfile", "-", "--error-logfile", "-"]

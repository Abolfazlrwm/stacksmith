"""Minimal Django settings for the CI stub image.

Mirrors the runtime contract the production compose files expect
(POSTGRES_* env vars, REDIS_URL, CELERY_BROKER_URL) without any docubot
specifics.
"""
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "stub-insecure-key")

DEBUG = os.environ.get("DEBUG", "0") == "1"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "probe",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "docubot"),
        "USER": os.environ.get("POSTGRES_USER", "docubot"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True

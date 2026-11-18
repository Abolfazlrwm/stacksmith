"""Django settings for the docubot deployment smoke target."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"

# ALLOWED_HOSTS — never default to "*" in production. Local dev can pass
# "*" explicitly via DJANGO_ALLOWED_HOSTS=*, but the default is the
# canonical hostname plus the loopback addresses the in-container
# readiness probe uses, so a misconfigured prod deploy fails closed.
_ALLOWED_HOSTS_RAW = os.environ.get(
    "DJANGO_ALLOWED_HOSTS",
    "docubot.example.com,localhost,127.0.0.1",
)
ALLOWED_HOSTS = [h.strip() for h in _ALLOWED_HOSTS_RAW.split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "rest_framework",
    "corsheaders",
    "health",
    "documents",
    "rag",
    "chat",
]

# SecurityMiddleware must be first to set HSTS / redirect / content-type
# headers. CsrfViewMiddleware and XFrameOptionsMiddleware are
# defense-in-depth for the admin and future session-backed views — the
# chat and documents APIs are not CSRF-protected today (the reverse
# proxy authenticates and sets X-Docubot-Owner), but the admin and any
# future session view are.
#
# RateLimitMiddleware runs after CommonMiddleware (so request.path is
# resolved) and before auth — it must reject a flood before the view
# (and its LLM call) runs. See ADR-0038.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "config.ratelimit.RateLimitMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# Where uploaded documents are stored on the volume. Mounted into both the
# API container (writes here on upload) and the worker container (reads here
# during ingestion). See docker-compose.prod.yml for the volume mount.
DOCUBOT_UPLOAD_ROOT = os.environ.get("DOCUBOT_UPLOAD_ROOT", "/data/uploads")
# Max upload size the app will accept; nginx enforces a separate limit.
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024

# CORS — the single-page chat UI is served from the same origin in prod,
# but during local dev it may run from another port. Allow the explicit
# list, plus all origins when DEBUG=true for convenience.
CORS_ALLOWED_ORIGINS = [
    o for o in os.environ.get("DOCUBOT_CORS_ORIGINS", "http://localhost:5173").split(",")
    if o
]
CORS_ALLOW_ALL_ORIGINS = DEBUG

# --- Security headers (ADR-0037) -------------------------------------
# The reverse proxy (nginx) sets these too, but the app must not rely on
# the proxy alone — the canary probe and any direct port-8000 access
# (local dev, the readiness probe inside the container network) should
# also see hardened responses. Defense-in-depth.
#
# HSTS, content-type nosniff, referrer policy, and X-Frame-Options are
# safe to set unconditionally: they only affect response headers, never
# request routing, so they cannot break a health probe.
#
# SECURE_SSL_REDIRECT is the dangerous one: it issues a 301 to https://
# for every http:// request. The in-container readiness probe and the
# blue/green canary probe hit the app over plain HTTP (nginx has not
# terminated TLS yet at that point), so a redirect there makes the
# probe see 301 forever and the stack never reports healthy. Default
# off; operators turn it on explicitly with DJANGO_SSL_REDIRECT=true in
# the rare case where the app is directly internet-facing.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SSL_REDIRECT", "false").lower() == "true"
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0  # 1 year, prod only
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
# Belt and suspenders: even if SSL redirect is on, health probes must
# not be redirected (the in-container probe is always plain HTTP).
SECURE_REDIRECT_EXEMPT = [r"^/health/"]
X_FRAME_OPTIONS = "DENY"

# DRF — no per-credential auth yet; the reverse proxy sets X-Docubot-Owner
# after performing its own auth. See docs/security.md.
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "docubot"),
        "USER": os.environ.get("POSTGRES_USER", "docubot"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    }
}

# Celery
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Templates — the chat UI ships as a single HTML file under templates/.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Static files — served by the app in dev, by nginx in prod.
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"level":"%(levelname)s","name":"%(name)s","msg":"%(message)s"}',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "health": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "documents": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "rag": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "chat": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

"""Pytest configuration for the app test suite.

These tests run without a database — they target the pure functions
in `documents/ingestion.py` and the citation resolver in `chat/views.py`,
which only need a `list[RetrievalHit]` to work against.

We deliberately do NOT use the prod `config.settings` here: importing it
pulls in `django.contrib.auth` / `admin` / `sessions`, which eagerly
touch the DB at app-loading time. The minimal settings module below
contains only the apps whose models our tests actually import
(`documents`, `chat`, `rag`, `health`), so app loading never opens a
DB connection.
"""
import os
import sys
import types
from pathlib import Path

# Add the app directory to sys.path so `config`, `documents`, `chat`,
# `rag`, `health` are importable.
_APP_DIR = Path(__file__).resolve().parents[2] / "app"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

# Build a minimal settings module in memory. We avoid the prod
# `config.settings` because its INSTALLED_APPS pulls in contrib.auth,
# which loads the user model, which opens a DB connection at import
# time. Our tests do not need any of that — they exercise pure
# functions that import only `documents.models` (which imports
# pgvector.django.VectorField, a no-DB field descriptor).
_settings = types.ModuleType("tests_app_settings")
_settings.SECRET_KEY = "test-insecure-key"  # noqa: S105
_settings.DEBUG = False
_settings.ALLOWED_HOSTS = ["*"]
_settings.INSTALLED_APPS = [
    # The four docubot apps we actually test. Each loads its own
    # models.py at app-loading time; pgvector.django.VectorField is
    # just a Django field descriptor and does not touch the DB.
    "documents",
    "chat",
    "rag",
    "health",
    # contenttypes is required by Django's app loader plumbing.
    "django.contrib.contenttypes",
]
_settings.DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
_settings.USE_TZ = True
_settings.DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
_settings.CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}
_settings.CELERY_TASK_ALWAYS_EAGER = True
_settings.CELERY_BROKER_URL = "memory://"
_settings.STATIC_URL = "/static/"
# Settings the docubot apps read at import time.
_settings.DOCUBOT_UPLOAD_ROOT = "/tmp/docubot-test-uploads"
_settings.DOCUBOT_EMBED_PROVIDER = "stub"
_settings.DOCUBOT_LLM_PROVIDER = "stub"
_settings.DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
_settings.FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
_settings.LOGGING_CONFIG = None  # don't reconfigure logging during tests

sys.modules["tests_app_settings"] = _settings
os.environ["DJANGO_SETTINGS_MODULE"] = "tests_app_settings"

import django  # noqa: E402

django.setup()

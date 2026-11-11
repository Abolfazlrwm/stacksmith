"""WSGI entrypoint."""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Configure OpenTelemetry before Django loads the app, so the
# DjangoInstrumentor can patch the request handling.
from config.telemetry import setup_telemetry
setup_telemetry()


def application(environ, start_response):
    from django.core.wsgi import get_wsgi_application

    return get_wsgi_application()(environ, start_response)

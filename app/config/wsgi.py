"""WSGI entrypoint."""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def application(environ, start_response):
    from django.core.wsgi import get_wsgi_application

    return get_wsgi_application()(environ, start_response)

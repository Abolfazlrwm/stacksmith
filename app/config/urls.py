"""Root URL configuration."""
from pathlib import Path

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import TemplateView


def _read_version() -> str:
    """Read the app version from the VERSION file at repo root.

    The repo root is two parents up from this file (app/config/urls.py
    -> app/config -> app -> repo root). We read at import time so a
    deploy does not pay a stat on every request, and we fall back to
    '0.0.0+unknown' if the file is missing (the image is broken) rather
    than crashing the URL import.

    Before v1.2.3 this was hardcoded to '1.2.0' and drifted out of sync
    on every release — the v1.2.2 release shipped with /  reporting
    1.2.0. Reading the file keeps one source of truth.
    """
    try:
        version_file = Path(__file__).resolve().parents[2] / "VERSION"
        return version_file.read_text().strip()
    except (OSError, ValueError):
        return "0.0.0+unknown"


APP_VERSION = _read_version()


def health_root(request):
    """Tiny service root at / — curl-ing the host gives a useful response."""
    return JsonResponse({"service": "docubot", "version": APP_VERSION})


urlpatterns = [
    path("", health_root, name="root"),
    path("health/", include("health.urls")),
    path("admin/", admin.site.urls),

    # docubot API surface
    path("api/", include("documents.urls")),
    path("api/", include("chat.urls")),

    # Single-page chat UI (self-contained HTML, no build step).
    path("app/", TemplateView.as_view(
        template_name="chat.html",
        content_type="text/html; charset=utf-8",
    ), name="chat-ui"),

    # Interactive product+code showcase. Serves a single self-contained
    # HTML page (no build step, no backend calls) so a visitor can see
    # the product end-to-end and the code behind each feature side by
    # side. This is the GitHub-Pages deploy target too — the same file
    # is published at https://abolfazlrwm.github.io/stacksmith/.
    path("demo/", TemplateView.as_view(
        template_name="demo.html",
        content_type="text/html; charset=utf-8",
    ), name="demo-ui"),
]

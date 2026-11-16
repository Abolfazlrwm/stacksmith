"""Root URL configuration."""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import TemplateView


def health_root(request):
    """Tiny service root at / — curl-ing the host gives a useful response."""
    return JsonResponse({"service": "docubot", "version": "1.2.0"})


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
]

"""Root URL configuration."""
from django.urls import include, path

urlpatterns = [
    path("health/", include("health.urls")),
]

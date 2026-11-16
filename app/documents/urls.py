"""Documents URL routes."""
from django.urls import path

from .views import DocumentListCreateView

app_name = "documents"

urlpatterns = [
    path("documents/", DocumentListCreateView.as_view(), name="list-create"),
]

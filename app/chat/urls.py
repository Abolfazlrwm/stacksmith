"""Chat URL routes."""
from django.urls import path

from .views import ChatView

app_name = "chat"

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat"),
]

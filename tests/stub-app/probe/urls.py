from django.urls import path

from . import views

urlpatterns = [
    path("health/live/", views.live),
    path("health/ready/", views.ready),
]

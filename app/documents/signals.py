"""Signals — kick off ingestion when a Document is created."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Document


@receiver(post_save, sender=Document)
def queue_ingestion(sender, instance, created, **kwargs):
    """When a Document is first created, enqueue the ingest task."""
    if not created:
        return
    if instance.status != Document.Status.PENDING:
        return
    # Import lazily so the signal module does not require Celery at import time
    # (e.g. during makemigrations on a fresh checkout).
    from .tasks import ingest_document
    ingest_document.delay(instance.id)

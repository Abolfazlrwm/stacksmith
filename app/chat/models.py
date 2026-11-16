"""Conversation persistence — multi-turn chat history per user."""
from django.db import models


class Conversation(models.Model):
    """A conversation thread. Has many Messages."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.CharField(max_length=128, db_index=True)
    title = models.CharField(max_length=256, blank=True)

    class Meta:
        ordering = ("-updated_at",)


class Message(models.Model):
    """One turn in a conversation — a user question or an assistant answer."""

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    conversation = models.ForeignKey(
        Conversation, related_name="messages", on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Citations are stored as JSON so the UI can render them without a join.
    # Each entry: {chunk_id, document_id, document_title, ordinal, score, snippet}.
    citations = models.JSONField(default=list, blank=True)
    retrieved_count = models.PositiveIntegerField(default=0)
    model = models.CharField(max_length=64, blank=True)
    usage = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("conversation", "created_at")

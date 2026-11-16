"""Document and Chunk models — the corpus that docubot answers from.

A Document is one uploaded file (PDF, Markdown, plain text). On upload it is
queued for ingestion; ingestion extracts plain text, splits it into Chunks of
~512 tokens, and stores each Chunk with a pgvector embedding so retrieval can
find the most semantically relevant passages for a chat query.

The embedding itself is produced by the `rag` app (see rag/embeddings.py),
which keeps the model and provider choice in one place.
"""
from django.db import models
from pgvector.django import VectorField


class Document(models.Model):
    """One uploaded document. Has many Chunks after ingestion."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending ingestion"
        INGESTING = "ingesting", "Ingesting"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    class Kind(models.TextChoices):
        PDF = "pdf", "PDF"
        MARKDOWN = "markdown", "Markdown"
        TEXT = "text", "Plain text"

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Source identity
    title = models.CharField(max_length=512)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    source = models.CharField(
        max_length=1024, blank=True,
        help_text="Original filename or URL the document came from.",
    )
    checksum = models.CharField(
        max_length=64, db_index=True,
        help_text="SHA-256 of the raw bytes; dedup key.",
    )

    # Lifecycle
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING,
        db_index=True,
    )
    raw_text = models.TextField(
        blank=True,
        help_text="The full extracted plain text, kept for re-chunking.",
    )
    chunk_count = models.PositiveIntegerField(default=0)
    byte_size = models.PositiveBigIntegerField(default=0)
    error = models.TextField(blank=True)

    # Owner — multi-user: each user's collections are isolated.
    owner = models.CharField(
        max_length=128, blank=True, db_index=True,
        help_text="Opaque owner identifier (e.g. username, API key id).",
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "checksum"], name="uniq_owner_checksum",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.kind}, {self.status})"


class Chunk(models.Model):
    """One retrievable passage of a Document, with its embedding."""

    document = models.ForeignKey(
        Document, related_name="chunks", on_delete=models.CASCADE,
    )
    ordinal = models.PositiveIntegerField(
        help_text="Position of this chunk within the document (0-based).",
    )
    text = models.TextField()
    token_count = models.PositiveIntegerField(default=0)

    # pgvector embedding. Dimension depends on the model; all-MiniLM-L6-v2
    # is 384 dims. The column is created by the migration; the dimension is
    # declared here so Django + django-pgvector manage the schema.
    embedding = VectorField(dimensions=384, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("document", "ordinal")
        constraints = [
            models.UniqueConstraint(
                fields=["document", "ordinal"], name="uniq_doc_ordinal",
            ),
        ]
        indexes = [
            # HNSW index for fast approximate nearest-neighbor search.
            # Built in a migration (see 0002_chunk_vector_index).
        ]

    def __str__(self) -> str:
        return f"Chunk#{self.ordinal} of {self.document_id}"

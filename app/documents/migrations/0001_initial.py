"""Initial migration: Document + Chunk tables.

The pgvector extension itself is enabled by the `health` app's 0001 migration
(which runs `CREATE EXTENSION IF NOT EXISTS vector`); this migration only
creates the tables that use vector-typed columns.
"""
from django.db import migrations, models

from pgvector.django import VectorField


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("health", "0001_enable_pgvector"),
    ]

    operations = [
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=512)),
                ("kind", models.CharField(choices=[("pdf", "PDF"), ("markdown", "Markdown"), ("text", "Plain text")], max_length=16)),
                ("source", models.CharField(blank=True, help_text="Original filename or URL the document came from.", max_length=1024)),
                ("checksum", models.CharField(db_index=True, help_text="SHA-256 of the raw bytes; dedup key.", max_length=64)),
                ("status", models.CharField(choices=[("pending", "Pending ingestion"), ("ingesting", "Ingesting"), ("ready", "Ready"), ("failed", "Failed")], db_index=True, default="pending", max_length=16)),
                ("raw_text", models.TextField(blank=True, help_text="The full extracted plain text, kept for re-chunking.")),
                ("chunk_count", models.PositiveIntegerField(default=0)),
                ("byte_size", models.PositiveBigIntegerField(default=0)),
                ("error", models.TextField(blank=True)),
                ("owner", models.CharField(blank=True, db_index=True, help_text="Opaque owner identifier (e.g. username, API key id).", max_length=128)),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="Chunk",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ordinal", models.PositiveIntegerField(help_text="Position of this chunk within the document (0-based).")),
                ("text", models.TextField()),
                ("token_count", models.PositiveIntegerField(default=0)),
                ("embedding", VectorField(blank=True, dimensions=384, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("document", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="chunks", to="documents.document")),
            ],
            options={
                "ordering": ("document", "ordinal"),
            },
        ),
        migrations.AddConstraint(
            model_name="document",
            constraint=models.UniqueConstraint(fields=("owner", "checksum"), name="uniq_owner_checksum"),
        ),
        migrations.AddConstraint(
            model_name="chunk",
            constraint=models.UniqueConstraint(fields=("document", "ordinal"), name="uniq_doc_ordinal"),
        ),
        migrations.AddIndex(
            model_name="document",
            index=models.Index(fields=("owner", "status"), name="documents_d_owner_13a9c8_idx"),
        ),
    ]

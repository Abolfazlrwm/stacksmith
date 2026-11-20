"""Celery task: ingest a Document — extract, chunk, embed, persist.

This is the async half of the upload flow. The HTTP handler stores the raw
bytes and creates a Document row (status=pending); this task does the heavy
work off the request thread.
"""
from __future__ import annotations

import hashlib
import logging

from celery import shared_task
from django.db import transaction

from .models import Chunk, Document

log = logging.getLogger(__name__)


@shared_task(
    name="documents.ingest_document",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,
    retry_backoff_max=600,
    max_retries=3,
)
def ingest_document(self, document_id: int) -> None:
    """Ingest a Document: extract text, split chunks, embed each, persist.

    Idempotent — if the document is already READY or INGESTING, the task
    exits early. If it was previously FAILED, this retried run clears the
    chunks and starts over.
    """
    # Import lazily so the worker does not fail to boot if extraction
    # libraries are missing (the API still works for /health/ etc.).
    from .ingestion import extract, split_chunks, approx_token_count
    from rag.embeddings import embed_texts

    with transaction.atomic():
        doc = (
            Document.objects
            .select_for_update()
            .filter(id=document_id)
            .first()
        )
        if doc is None:
            log.warning("ingest_document: document %s not found", document_id)
            return
        if doc.status == Document.Status.READY:
            log.info("ingest_document: %s already ready, skipping", doc.id)
            return
        if doc.status == Document.Status.INGESTING:
            # A previous run crashed mid-way; clean up its partial chunks.
            doc.chunks.all().delete()
        doc.status = Document.Status.INGESTING
        doc.error = ""
        doc.save(update_fields=["status", "error", "updated_at"])

    try:
        # Re-read the raw bytes. In production these live on object storage;
        # for the local single-VPS deployment they live in the volume the
        # API wrote them to. We store the checksum on the Document so the
        # API can dedup before enqueuing ingestion.
        raw = _read_raw_bytes(doc)
        if raw is None:
            raise RuntimeError(
                f"raw bytes for document {doc.id} are no longer available; "
                "re-upload the file to ingest it."
            )

        # Verify checksum — guards against silent corruption on the volume.
        actual_sha = hashlib.sha256(raw).hexdigest()
        if actual_sha != doc.checksum:
            raise RuntimeError(
                f"checksum mismatch for document {doc.id}: "
                f"expected {doc.checksum}, got {actual_sha}"
            )

        extracted = extract(raw, doc.kind)
        chunks_text = split_chunks(extracted.text)

        if not chunks_text:
            doc.status = Document.Status.READY
            doc.raw_text = extracted.text
            doc.chunk_count = 0
            doc.save(update_fields=["status", "raw_text", "chunk_count",
                                     "updated_at"])
            return

        # Embed all chunks in one batch — the local model is most efficient
        # when given a list. The provider may raise; we let it propagate to
        # the retry policy.
        embeddings = embed_texts(chunks_text)

        with transaction.atomic():
            doc.chunks.all().delete()
            chunk_objs = [
                Chunk(
                    document=doc,
                    ordinal=i,
                    text=text,
                    token_count=approx_token_count(text),
                    embedding=vec,
                )
                for i, (text, vec) in enumerate(zip(chunks_text, embeddings))
            ]
            Chunk.objects.bulk_create(chunk_objs, batch_size=64)

            doc.raw_text = extracted.text
            doc.chunk_count = len(chunk_objs)
            doc.byte_size = len(raw)
            doc.status = Document.Status.READY
            doc.save(update_fields=["raw_text", "chunk_count", "byte_size",
                                     "status", "updated_at"])

        log.info("ingest_document: %s ready, %d chunks",
                 doc.id, len(chunk_objs))

    except Exception as exc:
        # Re-read in a fresh transaction to record the failure.
        Document.objects.filter(id=document_id).update(
            status=Document.Status.FAILED,
            error=str(exc)[:2000],
        )
        log.exception("ingest_document: %s failed", document_id)
        raise


def _read_raw_bytes(doc: Document) -> bytes | None:
    """Read the raw bytes for a document from the local upload volume.

    The path is built from the owner + checksum so it is stable across
    restarts. Returns None if the file is missing (e.g. volume rotated).
    """
    import os
    from django.conf import settings

    from .storage import owner_dir_name

    upload_root = getattr(settings, "DOCUBOT_UPLOAD_ROOT", "/data/uploads")
    # The owner in a DB row originally came from a request header; projecting
    # it through owner_dir_name() keeps the derived path traversal-proof even
    # for rows written before this hardening.
    path = os.path.join(upload_root, owner_dir_name(doc.owner), doc.checksum)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        return fh.read()

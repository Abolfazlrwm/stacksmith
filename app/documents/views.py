"""Document upload API.

POST /api/documents/ with a multipart file upload -> creates a Document
(in status=pending), writes the raw bytes to the upload volume, and the
post_save signal enqueues the ingest task.

GET /api/documents/ -> list this owner's documents with their ingestion
status, so the UI can show a progress indicator.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from django.conf import settings
from django.http import HttpRequest
from rest_framework import serializers, status
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response

from .ingestion import detect_kind
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ("id", "title", "kind", "source", "status", "chunk_count",
                  "byte_size", "error", "created_at", "updated_at")
        read_only_fields = ("id", "status", "chunk_count", "byte_size",
                            "error", "created_at", "updated_at", "kind")


class DocumentCreateSerializer(serializers.Serializer):
    """Multipart upload: title (optional) + file."""
    file = serializers.FileField()
    title = serializers.CharField(max_length=512, required=False, allow_blank=True)


class DocumentListCreateView(ListCreateAPIView):
    """GET /api/documents/ — list; POST /api/documents/ — upload."""

    serializer_class = DocumentSerializer
    queryset = Document.objects.all()

    def get_queryset(self):
        owner = _owner(self.request)
        return self.queryset.filter(owner=owner)

    def create(self, request: HttpRequest, *args, **kwargs):
        owner = _owner(request)
        ser = DocumentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        upload = ser.validated_data["file"]
        title = ser.validated_data.get("title") or Path(upload.name).stem

        # Read fully into memory — these are text documents, not videos.
        # A 50 MB cap is enforced at the web server; here we just hash+store.
        data = upload.read()
        checksum = hashlib.sha256(data).hexdigest()

        # Dedup: if this owner already has this exact file, return the
        # existing row instead of re-ingesting.
        existing = Document.objects.filter(owner=owner, checksum=checksum).first()
        if existing is not None:
            return Response(
                DocumentSerializer(existing).data,
                status=status.HTTP_200_OK,
            )

        try:
            kind = detect_kind(upload.name, getattr(upload, "content_type", None))
        except ValueError as exc:
            return Response({"detail": str(exc)},
                            status=status.HTTP_400_BAD_REQUEST)

        # Persist the raw bytes to the upload volume BEFORE creating the
        # row, so the ingest task can read them.
        upload_root = Path(getattr(settings, "DOCUBOT_UPLOAD_ROOT", "/data/uploads"))
        upload_dir = upload_root / (owner or "_shared")
        upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_dir / checksum
        # Write atomically: write to a tmp file, then rename.
        tmp = path.with_suffix(".tmp")
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)

        doc = Document.objects.create(
            owner=owner,
            title=title,
            kind=kind,
            source=upload.name,
            checksum=checksum,
            byte_size=len(data),
            status=Document.Status.PENDING,
        )
        # The post_save signal enqueues the ingest task; we just return.
        return Response(
            DocumentSerializer(doc).data,
            status=status.HTTP_201_CREATED,
        )


def _owner(request: HttpRequest) -> str:
    """Resolve owner from X-Docubot-Owner header (set by the reverse proxy)."""
    return request.headers.get("X-Docubot-Owner", "anonymous")

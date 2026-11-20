"""Document upload API.

POST /api/documents/ with a multipart file upload -> creates a Document
(in status=pending), writes the raw bytes to the upload volume, and the
post_save signal enqueues the ingest task.

GET /api/documents/ -> list this owner's documents with their ingestion
status, so the UI can show a progress indicator.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path, PurePath

from django.conf import settings
from django.http import HttpRequest
from rest_framework import serializers, status
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response

from .ingestion import validate_upload
from .models import Document
from .storage import log_safe, owner_dir_name

logger = logging.getLogger(__name__)


# Cap the uploaded filename length so a malicious client cannot send a
# 10 MB filename string. The stored bytes are keyed by checksum, so the
# filename only matters for display + extension allow-listing.
MAX_FILENAME_LEN = 255

# Upload bytes are stored under their SHA-256 hex digest; the strict
# whitelist is both a correctness guard and a taint barrier so the
# digest is provably the only file-name component derived from content.
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


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

        # Reject path-traversal payloads and absurdly long names BEFORE
        # any disk I/O. We do not trust the client's filename for
        # storage (we key by checksum) but we still echo it back in the
        # response, so it must be a bare filename, not a path.
        name = upload.name or ""
        if not name or len(name) > MAX_FILENAME_LEN:
            return Response(
                {"detail": f"filename must be 1..{MAX_FILENAME_LEN} chars"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if PurePath(name).name != name or "/" in name or "\\" in name:
            return Response(
                {"detail": "filename must not contain path separators"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        title = ser.validated_data.get("title") or Path(name).stem

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

        # Validate BEFORE writing to disk — extension allow-list + magic
        # bytes + UTF-8 check. (ADR-0037.) Raises ValueError with a
        # user-facing message.
        try:
            kind = validate_upload(name, data)
        except ValueError as exc:
            # The validator's message is internal text; echo a generic reason
            # to the client and keep the specifics in the server log only.
            # Both the filename and the owner header are attacker-controlled,
            # so they are projected through log_safe() first: a raw CR/LF in
            # either value could forge or split log entries (py/log-injection).
            logger.warning("rejected upload %s for owner %s: %s",
                           log_safe(name), log_safe(owner), log_safe(str(exc)))
            return Response({"detail": "invalid or unsupported file"},
                            status=status.HTTP_400_BAD_REQUEST)

        # The stored filename is the hex digest, never the client-supplied
        # name; the whitelist guard pins the value to [0-9a-f]{64} so the
        # path below is provably checksum-keyed (py/path-injection barrier).
        if not _SHA256_HEX.fullmatch(checksum):
            return Response({"detail": "checksum computation failed"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Persist the raw bytes to the upload volume BEFORE creating the
        # row, so the ingest task can read them. The candidate path is built
        # from the header-derived owner (projected onto a safe charset by
        # owner_dir_name()) and the content checksum, then normalized and
        # proven to stay under the upload root: the startswith check on the
        # normalized candidate is the canonical traversal guard, so on this
        # branch the target is provably inside the upload volume.
        upload_root = getattr(settings, "DOCUBOT_UPLOAD_ROOT", "/data/uploads")
        root_norm = os.path.normpath(upload_root)
        target = os.path.normpath(
            os.path.join(root_norm, owner_dir_name(owner), checksum))
        if not target.startswith(root_norm + os.sep):
            logger.warning("upload %s for owner %s: target escapes upload root",
                           log_safe(name), log_safe(owner))
            return Response({"detail": "invalid upload target"},
                            status=status.HTTP_400_BAD_REQUEST)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        # Write atomically: write to a tmp file, then rename.
        tmp = target + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, target)

        doc = Document.objects.create(
            owner=owner,
            title=title,
            kind=kind,
            source=name,
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

"""Pytest bootstrap for the docubot app unit suite.

These tests cover the pure-logic layers of the product (text extraction,
chunking, the embedding stub, the LLM adapters, request/response
serializers, citation resolution, and the health views) — the parts that
can be proven without a database. No test touches the ORM, so the suite
runs anywhere Python runs, including CI without postgres/pgvector and
without the torch/sentence-transformers wheels (the embedding layer is
exercised through its documented stub provider).

DB-backed behavior (upload → ingest → retrieve → chat end-to-end) is
covered by the smoke stack, the demo corpus, and the drill workflows.
"""
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent  # the `app/` directory
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

# Real production settings — the unit suite proves the wiring that ships.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# Belt-and-braces so an accidental real provider call cannot reach the
# network: every test that cares sets these explicitly via monkeypatch.
os.environ.setdefault("DOCUBOT_EMBED_PROVIDER", "stub")
os.environ.setdefault("DOCUBOT_LLM_PROVIDER", "stub")
# Django's test client sends Host: testserver. Production settings
# default ALLOWED_HOSTS to a closed list (ADR-0037), so tests that hit
# the client would 400 with DisallowedHost unless we add it. Set before
# django.setup() so the settings module sees it.
_existing = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
if "testserver" not in _existing:
    os.environ["DJANGO_ALLOWED_HOSTS"] = (
        f"{_existing},testserver" if _existing else "testserver"
    )

import django  # noqa: E402

django.setup()

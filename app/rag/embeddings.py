"""Embedding providers — turn text into vectors.

Default: a local sentence-transformers model that runs on the same VPS as
the app, so documents never leave the host. This is the whole point of
self-hosting docubot.

Production override: set DOCUBOT_EMBED_PROVIDER=openai to use OpenAI's
embedding API. Useful when you already pay for OpenAI and want the larger
1536-dim vectors; in that case also set the dimension in settings and the
Chunk model migration accordingly.

This module is imported lazily by the documents task, so a missing optional
dependency (e.g. sentence-transformers not installed in CI) does not break
the app — it only breaks ingestion.
"""
from __future__ import annotations

import logging
import os
from typing import Sequence

log = logging.getLogger(__name__)


# All-MiniLM-L6-v2 is 384-dim. If you change the provider, change this and
# run a migration that alters the `embedding` column dimension.
EMBEDDING_DIM = 384
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"


def get_provider() -> str:
    """Which provider are we using? Defaults to 'local'."""
    return os.environ.get("DOCUBOT_EMBED_PROVIDER", "local").lower()


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns one vector per input.

    Dispatches on DOCUBOT_EMBED_PROVIDER:
      - local   (default) — sentence-transformers on the VPS
      - openai            — OpenAI text-embedding-3-small (1536-dim)
      - stub              — deterministic hash-based vectors (no model, no
                            network). For CI and `make demo` only; not for
                            production because the vectors are not
                            semantically meaningful.
    """
    if not texts:
        return []
    provider = get_provider()
    if provider == "local":
        return _embed_local(texts)
    if provider == "openai":
        return _embed_openai(texts)
    if provider == "stub":
        return _embed_stub(texts)
    raise NotImplementedError(f"unsupported embed provider: {provider!r}")


def _embed_stub(texts: Sequence[str]) -> list[list[float]]:
    """Deterministic hash-based embeddings for tests.

    Each text is hashed to seed a small PRNG that fills a 384-dim vector,
    so the same text always produces the same vector. The vectors are NOT
    semantically meaningful — retrieval will only match exact or
    near-exact text — which is exactly what tests and the demo need.
    """
    import hashlib
    import random

    out: list[list[float]] = []
    for text in texts:
        seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
        rng = random.Random(seed)
        vec = [rng.uniform(-1.0, 1.0) for _ in range(EMBEDDING_DIM)]
        # Normalize to unit length so cosine distance behaves.
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        out.append([v / norm for v in vec])
    return out


def _embed_local(texts: Sequence[str]) -> list[list[float]]:
    """Run the sentence-transformers model on the host.

    The model is loaded once and cached on the module so repeated calls are
    fast. Downloading the model on first use requires network access; in an
    air-gapped deployment, pre-populate the HF cache or vendor the model.
    """
    global _LOCAL_MODEL
    if _LOCAL_MODEL is None:
        log.info("[rag] loading sentence-transformers model %s",
                 DEFAULT_MODEL_NAME)
        from sentence_transformers import SentenceTransformer
        _LOCAL_MODEL = SentenceTransformer(
            DEFAULT_MODEL_NAME,
            device=os.environ.get("DOCUBOT_EMBED_DEVICE", "cpu"),
        )
    # The model returns a numpy array; convert to plain Python lists so
    # the ORM can store them via pgvector.
    vectors = _LOCAL_MODEL.encode(list(texts), show_progress_bar=False)
    return [list(map(float, v)) for v in vectors]


def _embed_openai(texts: Sequence[str]) -> list[list[float]]:
    """OpenAI embeddings. Requires OPENAI_API_KEY and a 1536-dim migration."""
    from openai import OpenAI
    client = OpenAI()  # picks up OPENAI_API_KEY from the environment
    resp = client.embeddings.create(
        input=list(texts),
        model="text-embedding-3-small",
    )
    # OpenAI returns embeddings in input order.
    return [list(map(float, d.embedding)) for d in resp.data]


# Module-level cache for the local model. Not thread-safe across workers,
# but Celery workers are prefork — each worker process gets its own copy.
_LOCAL_MODEL = None

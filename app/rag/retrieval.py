"""Retrieval — find the most relevant Chunks for a query.

Uses pgvector's cosine-distance operator (`<=>`) for ANN search over the
HNSW index created in the documents migration.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from documents.models import Chunk, Document


@dataclass
class RetrievalHit:
    """One retrieved passage, with everything the chat layer needs to cite it."""
    chunk_id: int
    document_id: int
    document_title: str
    ordinal: int
    text: str
    score: float  # similarity, higher is better (1 - cosine_distance)


def retrieve(query: str, *, owner: str = "", top_k: int = 5,
             min_score: float = 0.20) -> list[RetrievalHit]:
    """Find the top_k chunks most similar to `query`, restricted to `owner`.

    `owner` is critical for multi-user isolation: user A must not retrieve
    from user B's documents. Pass the same owner string that was set on the
    Document rows.
    """
    from .embeddings import embed_texts

    if not query.strip():
        return []

    # Embed the query with the same model/provider used for chunks.
    qvec = embed_texts([query])[0]

    # pgvector cosine-distance search, restricted to this owner's documents.
    # We join to Document so we can return the title for citation, and so we
    # can filter on status=READY (don't retrieve from a half-ingested doc).
    qs = (
        Chunk.objects
        .select_related("document")
        .filter(document__status=Document.Status.READY)
    )
    if owner:
        qs = qs.filter(document__owner=owner)

    # Ordered by cosine distance ascending (most similar first).
    qs = qs.annotate(distance=models_pgvector_distance(qvec)) \
        .order_by("distance")[:top_k]

    hits: list[RetrievalHit] = []
    for chunk in qs:
        # Convert distance (0=identical, 2=opposite) to similarity in [0,1].
        sim = 1.0 - float(chunk.distance)
        if sim < min_score:
            continue
        hits.append(RetrievalHit(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_title=chunk.document.title,
            ordinal=chunk.ordinal,
            text=chunk.text,
            score=sim,
        ))
    return hits


# Tiny shim so the import inside `retrieve` works without polluting the
# top-level namespace with django-pgvector internals. `pgvector.django`
# exposes a `CosineDistance` expression; we use it through a deferred
# import to keep this module importable even if pgvector is not installed.
def models_pgvector_distance(vec):
    from pgvector.django import CosineDistance
    return CosineDistance("embedding", vec)

"""Unit tests for rag.embeddings — dispatch and the deterministic stub.

The heavy sentence-transformers model is a lazy import (see the module
docstring: "a missing optional dependency ... does not break the app"),
so these tests exercise the documented stub provider and the dispatch
contract without downloading anything.
"""
from __future__ import annotations

import pytest

from rag import embeddings


def test_stub_is_deterministic(monkeypatch):
    monkeypatch.setenv("DOCUBOT_EMBED_PROVIDER", "stub")
    a = embeddings.embed_texts(["the same text"])
    b = embeddings.embed_texts(["the same text"])
    assert a == b


def test_stub_vector_shape_and_unit_norm(monkeypatch):
    monkeypatch.setenv("DOCUBOT_EMBED_PROVIDER", "stub")
    vec = embeddings.embed_texts(["some document text"])[0]
    assert len(vec) == embeddings.EMBEDDING_DIM
    norm = sum(v * v for v in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-9


def test_stub_preserves_input_order_and_count(monkeypatch):
    monkeypatch.setenv("DOCUBOT_EMBED_PROVIDER", "stub")
    texts = ["alpha", "beta", "gamma"]
    out = embeddings.embed_texts(texts)
    assert len(out) == 3
    assert out[0] == embeddings.embed_texts(["alpha"])[0]
    assert out[1] == embeddings.embed_texts(["beta"])[0]
    assert out[2] == embeddings.embed_texts(["gamma"])[0]


def test_stub_different_texts_get_different_vectors(monkeypatch):
    monkeypatch.setenv("DOCUBOT_EMBED_PROVIDER", "stub")
    a, b = embeddings.embed_texts(["one thing", "another thing"])
    assert a != b


def test_embed_texts_empty_input_is_empty():
    assert embeddings.embed_texts([]) == []


def test_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("DOCUBOT_EMBED_PROVIDER", "psychic")
    with pytest.raises(NotImplementedError, match="psychic"):
        embeddings.embed_texts(["text"])


def test_default_provider_is_local(monkeypatch):
    monkeypatch.delenv("DOCUBOT_EMBED_PROVIDER", raising=False)
    assert embeddings.get_provider() == "local"


def test_local_provider_defers_import(monkeypatch):
    """The local path must not import torch/sentence-transformers until used.

    This is the contract the module docstring promises: a missing optional
    dependency breaks ingestion, not the app. We prove the import is lazy
    by checking the model cache is empty and the heavy wheels are absent
    from sys.modules after dispatch on a provider that never loads them.
    """
    monkeypatch.setenv("DOCUBOT_EMBED_PROVIDER", "stub")
    embeddings.embed_texts(["x"])
    assert embeddings._LOCAL_MODEL is None
    assert "sentence_transformers" not in __import__("sys").modules

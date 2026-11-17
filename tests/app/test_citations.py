"""Unit tests for chat/views.py — the citation resolver.

`_resolve_citations` maps `[1]`, `[2]`, ... markers in the model's answer
back to the actual retrieved chunks. It is the function that turns an
LLM's prose into the structured `citations` list the UI renders.

These tests use a tiny stub object that quacks like `RetrievalHit` —
no DB, no pgvector, no LLM call. They cover the three documented
behaviors: explicit citations, missing-citation fallback, and bounds
safety on out-of-range markers.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

# We import the function under test through Django setup (conftest.py
# calls django.setup() before this module is collected).
from chat.views import _resolve_citations


@dataclass
class _Hit:
    """Minimal stand-in for rag.retrieval.RetrievalHit.

    `_resolve_citations` reads .text, .score, .chunk_id, .document_id,
    .document_title, .ordinal — and nothing else — so this is enough.
    """
    chunk_id: int
    document_id: int
    document_title: str
    ordinal: int
    text: str
    score: float


def _hits(n: int) -> list[_Hit]:
    """Build n fake hits with monotonically decreasing scores.

    Each hit's text is ~350 chars so the snippet-truncation path
    (>300 chars → append "...") is exercised by the citation tests.
    """
    return [
        _Hit(
            chunk_id=i + 1,
            document_id=100 + i,
            document_title=f"doc-{i}",
            ordinal=i,
            text=f"passage number {i} " * 25,  # ~350 chars
            score=1.0 - (i * 0.1),  # 1.0, 0.9, 0.8, ...
        )
        for i in range(n)
    ]


# --- explicit citations -----------------------------------------------

class TestExplicitCitations:
    """When the model writes [1] / [2] / ..., we map them to the right hits."""

    def test_single_citation(self):
        hits = _hits(3)
        out = _resolve_citations("The answer is foo [1].", hits)
        assert len(out) == 1
        assert out[0]["chunk_id"] == 1
        assert out[0]["ordinal"] == 0
        assert out[0]["score"] == 1.0
        # Snippet is truncated to 300 chars with an ellipsis when longer.
        assert out[0]["snippet"].endswith("...")

    def test_multiple_citations_preserve_order_of_appearance(self):
        hits = _hits(5)
        # [3] appears before [1] in the text → out should be [doc-2, doc-0].
        text = "First [3], then [1]."
        out = _resolve_citations(text, hits)
        assert len(out) == 2
        assert out[0]["chunk_id"] == 3
        assert out[1]["chunk_id"] == 1

    def test_duplicate_markers_are_deduplicated(self):
        hits = _hits(3)
        text = "see [1] and also [1] again [1]."
        out = _resolve_citations(text, hits)
        assert len(out) == 1
        assert out[0]["chunk_id"] == 1

    def test_citation_includes_document_title(self):
        hits = _hits(2)
        out = _resolve_citations("answer [2].", hits)
        assert out[0]["document_title"] == "doc-1"

    def test_score_is_rounded_to_four_decimals(self):
        hits = [_Hit(chunk_id=1, document_id=10, document_title="t",
                     ordinal=0, text="x" * 50, score=0.123456789)]
        out = _resolve_citations("[1]", hits)
        assert out[0]["score"] == 0.1235


# --- bounds safety ---------------------------------------------------

class TestCitationBounds:
    """Out-of-range or malformed markers must not crash."""

    def test_marker_zero_is_ignored(self):
        # [0] is not a valid 1-indexed citation.
        hits = _hits(3)
        out = _resolve_citations("see [0].", hits)
        # No valid citations → fallback path: return all hits by score.
        assert len(out) == 3
        assert out[0]["chunk_id"] == 1  # highest score

    def test_marker_above_range_is_ignored(self):
        hits = _hits(2)
        out = _resolve_citations("see [99].", hits)
        # No valid citations → fallback path returns all 2 hits.
        assert len(out) == 2

    def test_marker_just_out_of_range(self):
        hits = _hits(3)
        # [4] is just past the end — must not index out of bounds.
        out = _resolve_citations("[1] and [4].", hits)
        # Only [1] is valid; fallback is not triggered because there
        # is at least one valid citation.
        assert len(out) == 1
        assert out[0]["chunk_id"] == 1

    def test_non_digit_markers_ignored(self):
        hits = _hits(2)
        # [abc] is not a digit, the regex does not match.
        out = _resolve_citations("see [abc] for more.", hits)
        # No valid citations → fallback returns all hits by score.
        assert len(out) == 2


# --- fallback when the model cites nothing ---------------------------

class TestFallbackCitations:
    """When the answer has no [N] markers, we return all hits ranked by
    score, so the UI can still show sources."""

    def test_no_markers_returns_all_hits_by_score(self):
        hits = _hits(3)
        out = _resolve_citations("The answer is foo bar baz.", hits)
        assert len(out) == 3
        # Score-ordered: 1.0, 0.9, 0.8 → chunk_ids 1, 2, 3.
        assert [c["chunk_id"] for c in out] == [1, 2, 3]

    def test_fallback_with_unordered_input_scores(self):
        # Hits passed in with non-monotonic scores — fallback must sort.
        hits = [
            _Hit(chunk_id=10, document_id=1, document_title="a",
                 ordinal=0, text="x" * 10, score=0.3),
            _Hit(chunk_id=20, document_id=1, document_title="b",
                 ordinal=0, text="y" * 10, score=0.9),
            _Hit(chunk_id=30, document_id=1, document_title="c",
                 ordinal=0, text="z" * 10, score=0.6),
        ]
        out = _resolve_citations("plain answer no markers", hits)
        assert [c["chunk_id"] for c in out] == [20, 30, 10]


# --- snippet shaping -------------------------------------------------

class TestSnippetShaping:
    """The snippet field is the user-facing excerpt — must be capped."""

    def test_short_text_returned_as_is(self):
        hits = [_Hit(chunk_id=1, document_id=1, document_title="t",
                     ordinal=0, text="short", score=1.0)]
        out = _resolve_citations("[1]", hits)
        assert out[0]["snippet"] == "short"
        assert not out[0]["snippet"].endswith("...")

    def test_long_text_truncated_to_300_chars_with_ellipsis(self):
        long_text = "x" * 1000
        hits = [_Hit(chunk_id=1, document_id=1, document_title="t",
                     ordinal=0, text=long_text, score=1.0)]
        out = _resolve_citations("[1]", hits)
        snip = out[0]["snippet"]
        assert len(snip) == 303  # 300 + "..."
        assert snip.endswith("...")
        assert snip.startswith("xxx")

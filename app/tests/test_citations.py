"""Unit tests for chat.views._resolve_citations — the citation contract.

`_resolve_citations` is a pure function: it maps the model's [1]/[2]
markers back to the retrieved chunks, dedupes them in order of first
appearance, and falls back to a score-ranked list when the model cited
nothing. These tests pin that contract — it is what the UI renders as
"sources".
"""
from __future__ import annotations

from dataclasses import dataclass

from chat.views import _resolve_citations


@dataclass
class FakeHit:
    chunk_id: int
    document_id: int
    document_title: str
    ordinal: int
    text: str
    score: float


def _hits():
    return [
        FakeHit(11, 1, "alpha.md", 0, "A" * 350, 0.91),
        FakeHit(22, 2, "beta.md", 3, "B text", 0.42),
        FakeHit(33, 3, "gamma.md", 1, "C text", 0.65),
    ]


def test_markers_map_to_the_right_chunks_in_first_appearance_order():
    text = "The answer is in [2] and also [3][1]."
    out = _resolve_citations(text, _hits())
    assert [c["chunk_id"] for c in out] == [22, 33, 11]


def test_repeated_markers_are_deduplicated():
    out = _resolve_citations("same source twice [1] ... [1] again [2]", _hits())
    assert [c["chunk_id"] for c in out] == [11, 22]


def test_out_of_range_markers_are_ignored():
    out = _resolve_citations("hallucinated [9] and [1]", _hits())
    assert [c["chunk_id"] for c in out] == [11]


def test_zero_marker_is_ignored():
    out = _resolve_citations("bad [0] marker [2]", _hits())
    assert [c["chunk_id"] for c in out] == [22]


def test_no_markers_falls_back_to_all_hits_by_score():
    out = _resolve_citations("the model cited nothing", _hits())
    assert [c["chunk_id"] for c in out] == [11, 33, 22]  # 0.91, 0.65, 0.42


def test_citation_payload_shape_and_snippet_truncation():
    out = _resolve_citations("[1]", _hits())
    first = out[0]
    assert first["document_title"] == "alpha.md"
    assert first["ordinal"] == 0
    assert first["score"] == 0.91
    assert len(first["snippet"]) == 300 + 3  # 300 chars + ellipsis
    assert first["snippet"].endswith("...")


def test_short_snippets_have_no_ellipsis():
    out = _resolve_citations("[2]", _hits())
    assert out[0]["snippet"] == "B text"

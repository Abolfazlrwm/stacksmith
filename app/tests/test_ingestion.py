"""Unit tests for documents.ingestion — extraction, chunking, kind detection.

The ingestion module is deliberately pure (no Django imports), so these
tests run without a database. The PDF test generates a real PDF in-memory
with PyMuPDF itself — no binary fixture committed.
"""
from __future__ import annotations

import pytest

from documents.ingestion import (
    CHUNK_CHARS,
    CHUNK_OVERLAP,
    approx_token_count,
    detect_kind,
    extract,
    extract_markdown,
    extract_pdf,
    extract_text,
    split_chunks,
)


# ---------------------------------------------------------------------------
# extraction
# ---------------------------------------------------------------------------


def test_extract_text_plain():
    out = extract_text("hello document\nsecond line\n".encode("utf-8"))
    assert "hello document" in out
    assert "second line" in out


def test_extract_text_tolerates_bad_bytes():
    out = extract_text(b"fine \xff\xfe bytes")
    assert "fine" in out  # errors="replace" keeps the readable part


def test_extract_markdown_strips_tags_and_keeps_text():
    md = b"# Heading\n\nSome paragraph with **bold** text.\n"
    out = extract_markdown(md)
    assert "Heading" in out
    assert "Some paragraph with" in out
    assert "bold" in out
    # No HTML tags survive the strip.
    assert "<h1>" not in out
    assert "<strong>" not in out


def test_extract_markdown_keeps_code_block_content():
    md = b"```python\nprint('hello')\n```"
    out = extract_markdown(md)
    assert "print('hello')" in out


def test_extract_pdf_roundtrip():
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "docubot pdf extraction test")
    data = doc.tobytes()
    doc.close()

    text = extract_pdf(data)
    assert "docubot pdf extraction test" in text


def test_extract_dispatches_on_kind():
    assert extract(b"plain", "text").kind == "text"
    assert extract(b"# md", "markdown").kind == "markdown"


def test_extract_rejects_unknown_kind():
    with pytest.raises(ValueError, match="unknown document kind"):
        extract(b"data", "spreadsheet")


# ---------------------------------------------------------------------------
# kind detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("filename", "mime", "expected"),
    [
        ("report.pdf", None, "pdf"),
        ("report.PDF", "application/octet-stream", "pdf"),
        ("notes.md", None, "markdown"),
        ("notes.markdown", None, "markdown"),
        ("notes.txt", None, "text"),
        ("notes.text", None, "text"),
        ("README", None, "text"),  # no extension → plain text by default
        ("notes", "text/plain", "text"),
    ],
)
def test_detect_kind(filename, mime, expected):
    assert detect_kind(filename, mime) == expected


@pytest.mark.parametrize("filename", ["data.csv", "image.png", "archive.zip"])
def test_detect_kind_rejects_unknown_extensions(filename):
    with pytest.raises(ValueError, match="cannot determine document kind"):
        detect_kind(filename)


def test_detect_kind_mime_can_force_text():
    assert detect_kind("blob", "text/plain") == "text"


# ---------------------------------------------------------------------------
# chunking
# ---------------------------------------------------------------------------


def test_split_chunks_empty_text():
    assert split_chunks("") == []


def test_split_chunks_short_text_is_one_chunk():
    assert split_chunks("a short document") == ["a short document"]


def test_split_chunks_respects_size():
    text = "\n\n".join(f"paragraph {i} " + "x" * 120 for i in range(30))
    chunks = split_chunks(text)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= CHUNK_CHARS


def test_split_chunks_prefers_paragraph_boundaries():
    # Every paragraph survives intact: with sizes well under `size` the
    # splitter must cut on paragraph boundaries, never inside a paragraph
    # (so no "para 1 wo" / "rd word" style truncation at chunk edges).
    text = "\n\n".join(f"para {i} " + "word " * 20 for i in range(40))
    chunks = split_chunks(text)
    assert len(chunks) > 1
    # The vocabulary is {para, word, <index>}; a cut inside a word would
    # leave a fragment ("wo", "rd") as some chunk's final token.
    vocab = {"para", "word"} | {str(i) for i in range(40)}
    for chunk in chunks:
        last = chunk.split()[-1]
        assert last in vocab, f"chunk ends mid-word: ...{chunk[-40:]!r}"


def test_split_chunks_overlaps_neighbors():
    text = "\n\n".join("content sentence " * 6 + str(i) for i in range(25))
    chunks = split_chunks(text)
    if len(chunks) < 2:
        pytest.skip("text fits in fewer than two chunks")
    # The configured overlap means the end of chunk i reappears at the
    # start of chunk i+1 (paragraph-boundary permitting).
    tail = chunks[0][-CHUNK_OVERLAP:]
    if tail.strip():
        assert tail.strip()[:20] in chunks[1][: len(tail) + CHUNK_OVERLAP + 50]


def test_split_chunks_hard_cut_fallback_for_mega_paragraph():
    text = "y" * (CHUNK_CHARS * 3)  # one paragraph, no newline anywhere
    chunks = split_chunks(text)
    assert len(chunks) == 3
    for chunk in chunks:
        assert chunk and len(chunk) <= CHUNK_CHARS


def test_approx_token_count_never_zero():
    assert approx_token_count("") == 1
    assert approx_token_count("x" * 40) == 10

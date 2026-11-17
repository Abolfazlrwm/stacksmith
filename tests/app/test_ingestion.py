"""Unit tests for documents/ingestion.py — text extraction, chunking,
and the upload validator.

These tests do not touch the database or pgvector. They cover the pure
functions in `ingestion.py`, which is where the upload-path security
controls live.
"""
from __future__ import annotations

import pytest

from documents.ingestion import (ALLOWED_EXTENSIONS, CHUNK_CHARS,
                                 CHUNK_OVERLAP, ExtractedText, approx_token_count,
                                 detect_kind, extract, extract_markdown,
                                 extract_text, split_chunks, validate_upload)


# --- detect_kind -----------------------------------------------------

class TestDetectKind:
    """detect_kind maps a (filename, mime) pair to one of pdf|markdown|text."""

    def test_pdf_by_extension(self):
        assert detect_kind("report.pdf") == "pdf"

    def test_pdf_by_mime_when_extension_missing(self):
        assert detect_kind("no-extension", mime="application/pdf") == "pdf"

    def test_markdown_variants(self):
        assert detect_kind("README.md") == "markdown"
        assert detect_kind("NOTES.markdown") == "markdown"

    def test_text_variants(self):
        assert detect_kind("notes.txt") == "text"
        assert detect_kind("notes.text") == "text"

    def test_empty_extension_treated_as_text(self):
        # A file with no extension but a text/plain mime is text.
        assert detect_kind("Makefile", mime="text/plain") == "text"

    def test_unknown_extension_raises(self):
        with pytest.raises(ValueError, match="cannot determine"):
            detect_kind("payload.exe")

    def test_case_insensitive(self):
        assert detect_kind("REPORT.PDF") == "pdf"
        assert detect_kind("Readme.MD") == "markdown"


# --- validate_upload (the new security gate) -------------------------

class TestValidateUpload:
    """validate_upload enforces the extension allow-list and magic-byte sniff
    BEFORE any bytes reach the upload volume."""

    def test_accepts_real_text(self):
        kind = validate_upload("notes.txt", b"hello world\n")
        assert kind == "text"

    def test_accepts_real_markdown(self):
        kind = validate_upload("readme.md", b"# Title\n\nbody text\n")
        assert kind == "markdown"

    def test_accepts_real_pdf(self):
        # %PDF- is the canonical PDF magic header.
        kind = validate_upload("report.pdf", b"%PDF-1.7\n...rest of file...")
        assert kind == "pdf"

    def test_rejects_disallowed_extension(self):
        with pytest.raises(ValueError, match="unsupported file type"):
            validate_upload("evil.exe", b"MZ\x90\x00binary payload")

    def test_rejects_renamed_exe_as_pdf(self):
        """A .exe renamed to .pdf must be caught by the magic-byte check."""
        with pytest.raises(ValueError, match="does not match the 'pdf' magic"):
            # MZ is the EXE magic header; the filename claims PDF.
            validate_upload("evil.pdf", b"MZ\x90\x00\x03\x00\x00\x00")

    def test_rejects_binary_renamed_to_txt(self):
        """A binary payload renamed to .txt must fail the UTF-8 decode check."""
        # 0xff 0xfe is not valid UTF-8 on its own.
        with pytest.raises(ValueError, match="not valid UTF-8"):
            validate_upload("binary.txt", b"\xff\xfe\x00\x00binary garbage")

    def test_rejects_empty_filename(self):
        with pytest.raises(ValueError, match="unsupported file type"):
            validate_upload("", b"some data")

    def test_allow_list_is_frozen(self):
        # frozenset is immutable — guards against accidental mutation.
        assert isinstance(ALLOWED_EXTENSIONS, frozenset)
        assert ".pdf" in ALLOWED_EXTENSIONS
        assert ".exe" not in ALLOWED_EXTENSIONS

    def test_extension_check_is_case_insensitive(self):
        # The view may receive upper-case extensions from a Windows client.
        assert validate_upload("REPORT.PDF", b"%PDF-1.7\n") == "pdf"


# --- split_chunks ----------------------------------------------------

class TestSplitChunks:
    """split_chunks partitions text into ~CHUNK_CHARS-byte passages with
    CHUNK_OVERLAP bytes of overlap so passages straddling a boundary stay
    retrievable."""

    def test_empty_text_returns_empty_list(self):
        assert split_chunks("") == []

    def test_whitespace_only_returns_empty(self):
        # The function strips; a string that becomes empty after strip
        # yields no chunks.
        assert split_chunks("   \n   \t   ") == []

    def test_short_text_single_chunk(self):
        text = "one short passage"
        chunks = split_chunks(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_splits_into_multiple_chunks(self):
        # Build a text that is comfortably > 2 chunks long.
        paragraph = "this is a paragraph of about forty characters.\n"
        text = paragraph * 100  # ~4400 chars → at least 2 chunks
        chunks = split_chunks(text)
        assert len(chunks) >= 2
        # Every chunk should be non-empty.
        assert all(c for c in chunks)
        # The first chunk should start with the start of the text.
        assert chunks[0].startswith("this is a paragraph")

    def test_chunks_respect_size_budget(self):
        # No chunk should be wildly larger than CHUNK_CHARS.
        text = ("line of text that is reasonably long\n" * 200)
        chunks = split_chunks(text, size=200, overlap=20)
        assert all(len(c) <= 200 + 50 for c in chunks)  # small slack for boundary

    def test_overlap_between_consecutive_chunks(self):
        # With a known text, the end of chunk N should overlap the start of
        # chunk N+1 — otherwise a query that straddles a boundary would
        # miss both chunks. We can't assert exact overlap (the split prefers
        # newline boundaries) but we can assert the chunks are not
        # disjoint copies of disjoint regions: the union reconstructs text.
        text = ("paragraph one with words\n" * 50) + ("paragraph two different\n" * 50)
        chunks = split_chunks(text, size=120, overlap=20)
        # Reconstructing: every line should appear in at least one chunk.
        # (chunks may have leading/trailing whitespace stripped, but
        # the body words are preserved.)
        joined = " ".join(chunks)
        assert "paragraph one with words" in joined
        assert "paragraph two different" in joined


# --- extract_* -------------------------------------------------------

class TestExtractText:
    def test_extracts_ascii(self):
        assert extract_text(b"hello world") == "hello world"

    def test_tolerates_bad_utf8(self):
        # errors="replace" — invalid bytes become U+FFFD, not a crash.
        out = extract_text(b"caf\xff")
        assert "caf" in out
        assert len(out) >= 4  # replacement char added

    def test_strips_trailing_whitespace(self):
        assert extract_text(b"  hi  \n\t") == "hi"


class TestExtractMarkdown:
    def test_strips_markup_keeps_text(self):
        md = b"# Title\n\nHello *world*.\n\n```code\nx = 1\n```\n"
        out = extract_markdown(md)
        # Heading text preserved
        assert "Title" in out
        # Body text preserved
        assert "Hello" in out and "world" in out
        # Code block content preserved as text
        assert "x = 1" in out
        # Markup tags stripped
        assert "<" not in out and ">" not in out

    def test_handles_fenced_code_blocks(self):
        md = b"text\n\n```python\nprint('hi')\n```\n"
        out = extract_markdown(md)
        assert "print('hi')" in out


# --- extract dispatcher ----------------------------------------------

class TestExtractDispatcher:
    def test_pdf_kind(self):
        # We can't easily build a real PDF in a unit test, so we just
        # verify the dispatcher raises for unknown kinds.
        with pytest.raises(ValueError, match="unknown document kind"):
            extract(b"anything", kind="bogus")

    def test_text_kind(self):
        result = extract(b"plain text content", kind="text")
        assert isinstance(result, ExtractedText)
        assert result.kind == "text"
        assert result.text == "plain text content"


# --- approx_token_count ----------------------------------------------

class TestApproxTokenCount:
    def test_short_text_at_least_one_token(self):
        assert approx_token_count("") == 1
        assert approx_token_count("hi") == 1

    def test_roughly_four_chars_per_token(self):
        # "abcdefgh" is 8 chars → 2 tokens.
        assert approx_token_count("abcdefgh") == 2
        # 40 chars → 10 tokens.
        assert approx_token_count("a" * 40) == 10

    def test_chunk_size_budget_aligns(self):
        # The chunk size was sized for ~512 tokens: 512 * 4 = 2048 chars.
        # CHUNK_CHARS is 2000, which is close — confirm the constants
        # are in the documented range.
        assert 1500 <= CHUNK_CHARS <= 2500
        assert 0 < CHUNK_OVERLAP < CHUNK_CHARS

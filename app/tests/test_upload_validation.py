"""Unit tests for documents.ingestion.validate_upload — the upload security gate.

These tests cover the three-layer defense that runs BEFORE any bytes are
written to the upload volume: extension allow-list, magic-byte sniff,
and UTF-8 decode check. No database, no Django — validate_upload is a
pure function over (filename, bytes).

The sibling test_ingestion.py covers detect_kind, extraction, chunking,
and token estimation. This file covers only validate_upload and the
constants it exposes.
"""
from __future__ import annotations

import pytest

from documents.ingestion import (
    ALLOWED_EXTENSIONS,
    MAGIC_SIGNATURES,
    validate_upload,
)


# ---------------------------------------------------------------------------
# happy path — the three accepted kinds
# ---------------------------------------------------------------------------

def test_validate_accepts_real_text():
    assert validate_upload("notes.txt", b"hello world\n") == "text"


def test_validate_accepts_real_markdown():
    assert validate_upload("readme.md", b"# Title\n\nbody text\n") == "markdown"


def test_validate_accepts_real_pdf():
    # %PDF- is the canonical PDF magic header.
    assert validate_upload("report.pdf", b"%PDF-1.7\nrest of file") == "pdf"


def test_validate_extension_check_is_case_insensitive():
    # Windows clients send upper-case extensions; the allow-list check
    # lowercases the name before matching.
    assert validate_upload("REPORT.PDF", b"%PDF-1.7\n") == "pdf"
    assert validate_upload("Readme.MD", b"# hi\n") == "markdown"
    assert validate_upload("NOTES.TXT", b"plain\n") == "text"


def test_validate_accepts_all_markdown_suffix_variants():
    assert validate_upload("a.markdown", b"# x\n") == "markdown"


def test_validate_accepts_all_text_suffix_variants():
    assert validate_upload("a.text", b"x\n") == "text"


# ---------------------------------------------------------------------------
# layer 1 — extension allow-list
# ---------------------------------------------------------------------------

def test_validate_rejects_disallowed_extension():
    with pytest.raises(ValueError, match="unsupported file type"):
        validate_upload("evil.exe", b"MZ\x90\x00binary payload")


def test_validate_rejects_empty_filename():
    with pytest.raises(ValueError, match="unsupported file type"):
        validate_upload("", b"some data")


def test_validate_rejects_archive_extensions():
    for bad in ("archive.zip", "data.csv", "image.png", "doc.docx"):
        with pytest.raises(ValueError, match="unsupported file type"):
            validate_upload(bad, b"whatever")


def test_allowed_extensions_is_frozen_set():
    # frozenset is immutable — guards against accidental mutation at
    # import time or in a test that tries to add to it.
    assert isinstance(ALLOWED_EXTENSIONS, frozenset)
    assert ".pdf" in ALLOWED_EXTENSIONS
    assert ".exe" not in ALLOWED_EXTENSIONS


def test_allowed_extensions_matches_documented_set():
    # If this set ever changes, the README, the API docs, and ADR-0037
    # all need to update with it. Pin the exact contents here.
    assert ALLOWED_EXTENSIONS == frozenset(
        {".pdf", ".md", ".markdown", ".txt", ".text"}
    )


# ---------------------------------------------------------------------------
# layer 2 — magic-byte sniff defeats name-spoofing
# ---------------------------------------------------------------------------

def test_validate_rejects_renamed_exe_as_pdf():
    """The headline attack: an EXE renamed to .pdf.

    The extension check passes (.pdf is in the allow-list), so the
    magic-byte sniff is the only thing that stops this. The first bytes
    of a Windows PE are 'MZ' (0x4d 0x5a), never '%PDF-'.
    """
    with pytest.raises(ValueError, match="does not match the 'pdf' magic"):
        validate_upload("evil.pdf", b"MZ\x90\x00\x03\x00\x00\x00binary")


def test_validate_rejects_renamed_zip_as_pdf():
    # PK\x03\x04 is the ZIP local-file-header signature.
    with pytest.raises(ValueError, match="does not match the 'pdf' magic"):
        validate_upload("payload.pdf", b"PK\x03\x04archive contents")


def test_magic_signatures_only_has_pdf_today():
    # Document the surface: PDF is the only kind with a portable magic
    # signature. Text and markdown fall back to the UTF-8 decode check.
    assert set(MAGIC_SIGNATURES.keys()) == {"pdf"}
    assert MAGIC_SIGNATURES["pdf"] == b"%PDF-"


# ---------------------------------------------------------------------------
# layer 3 — UTF-8 decode check defeats name-spoofing on text kinds
# ---------------------------------------------------------------------------

def test_validate_rejects_binary_renamed_to_txt():
    """A binary payload renamed to .txt must fail the UTF-8 decode check."""
    # 0xff 0xfe is the UTF-16 BOM, not valid UTF-8 on its own.
    with pytest.raises(ValueError, match="not valid UTF-8"):
        validate_upload("binary.txt", b"\xff\xfe\x00\x00binary garbage")


def test_validate_rejects_binary_renamed_to_markdown():
    with pytest.raises(ValueError, match="not valid UTF-8"):
        validate_upload("binary.md", b"\xff\xff\xff\xffnot text")


def test_validate_accepts_utf8_with_multibyte_chars():
    # Emoji + accented Latin + CJK — all valid UTF-8, must pass.
    payload = "héllo 世界 🚀\n".encode("utf-8")
    assert validate_upload("unicode.txt", payload) == "text"


def test_validate_accepts_empty_text_file():
    # An empty file decodes as empty UTF-8 — valid.
    assert validate_upload("empty.txt", b"") == "text"


def test_validate_accepts_empty_markdown_file():
    assert validate_upload("empty.md", b"") == "markdown"

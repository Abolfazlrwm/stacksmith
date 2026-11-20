"""Text extraction and chunking.

Pure functions, no Django imports, so they can be unit-tested in isolation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# A chunk is roughly 512 tokens. With our simple token heuristic (4 chars ≈ 1
# token) that is ~2000 characters. We overlap chunks by ~10% to keep passages
# that straddle a boundary retrievable.
CHUNK_CHARS = 2000
CHUNK_OVERLAP = 200


@dataclass
class ExtractedText:
    text: str
    kind: str


def extract_pdf(data: bytes) -> str:
    """Extract plain text from a PDF using PyMuPDF."""
    import fitz  # PyMuPDF — imported lazily so the app starts even if the
                # wheel is missing (CI drills run without it).
    text_parts: list[str] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text("text"))
    return "\n\n".join(text_parts).strip()


def extract_markdown(data: bytes) -> str:
    """Markdown: strip markup, keep text. We do not render to HTML because
    we want the *content*, not the rendered structure (headings become
    plain lines, code blocks stay as text)."""
    import markdown as md  # lazy import

    raw = data.decode("utf-8", errors="replace")
    # Convert to HTML, then strip tags. This preserves code blocks and lists
    # as readable text rather than mangling them.
    html = md.markdown(raw, extensions=["fenced_code", "tables"])
    text = re.sub(r"<[^>]+>", "", html)
    # Collapse excessive whitespace introduced by tag stripping.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text(data: bytes) -> str:
    """Plain text — decode UTF-8, tolerate bad bytes."""
    return data.decode("utf-8", errors="replace").strip()


def extract(data: bytes, kind: str) -> ExtractedText:
    """Dispatch on kind. Raises ValueError for unknown kinds."""
    if kind == "pdf":
        return ExtractedText(extract_pdf(data), "pdf")
    if kind == "markdown":
        return ExtractedText(extract_markdown(data), "markdown")
    if kind == "text":
        return ExtractedText(extract_text(data), "text")
    raise ValueError(f"unknown document kind: {kind!r}")


def split_chunks(text: str, *, size: int = CHUNK_CHARS,
                 overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split `text` into overlapping chunks of ~`size` characters.

    Splits on paragraph boundaries where possible to avoid cutting sentences
    mid-word. Falls back to a hard cut if a paragraph is longer than `size`.
    """
    if not text:
        return []
    # Normalize whitespace runs but keep newlines.
    text = re.sub(r"[ \t]+", " ", text).strip()
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = start + size
        if end >= n:
            chunks.append(text[start:].strip())
            break
        # Try to break on the next newline after `end - overlap` so the
        # chunk ends on a paragraph boundary.
        boundary = text.rfind("\n", end - overlap, end)
        if boundary == -1 or boundary <= start:
            boundary = end
        chunk = text[start:boundary].strip()
        if chunk:
            chunks.append(chunk)
        # Advance; if we landed on a newline, step past it.
        start = boundary + (1 if text[boundary:boundary + 1] == "\n" else 0)
    return chunks


def approx_token_count(text: str) -> int:
    """Cheap token estimate (~4 chars/token for English). Good enough for
    budget decisions; the real BPE count is not worth a tokenizer dep here."""
    return max(1, len(text) // 4)


def detect_kind(filename: str, mime: str | None = None) -> str:
    """Best-effort kind detection from a filename.

    Extensionless names (README, Makefile, ...) are treated as plain
    text; anything else that is not pdf/md/txt raises so the upload view
    can reject it with a 400 instead of silently ingesting binary bytes
    as text. (Before 2026-11-17 the final raise was unreachable: the
    text branch matched every filename via `endswith("")`, so a .zip or
    .csv upload produced garbage chunks instead of an error.)
    """
    name = filename.lower()
    if name.endswith(".pdf") or mime == "application/pdf":
        return "pdf"
    if name.endswith((".md", ".markdown")):
        return "markdown"
    if name.endswith((".txt", ".text")) or (mime and "text/plain" in mime):
        return "text"
    if "." not in name:
        return "text"
    raise ValueError(f"cannot determine document kind from {filename!r}")


# Explicit allow-list of accepted extensions. The upload view rejects
# anything not in this set BEFORE writing bytes to disk, so a request
# with a .exe payload never lands on the upload volume. Paired with
# the magic-byte check below, this defeats both name-spoofing and
# content-spoofing attacks on the upload path. (ADR-0037.)
ALLOWED_EXTENSIONS = frozenset({".pdf", ".md", ".markdown", ".txt", ".text"})

# Magic-byte signatures for the kinds we accept. The first bytes of the
# upload are checked against these so a file named `evil.pdf` whose
# content is an EXE is rejected at the door. PDF is the only kind with
# a portable signature today; text and markdown are validated by a
# UTF-8 decode check instead (see validate_upload).
MAGIC_SIGNATURES: dict[str, bytes] = {
    "pdf": b"%PDF-",  # PDF files always start with %PDF-
}


def validate_upload(filename: str, data: bytes) -> str:
    """Reject disallowed uploads before any bytes are written to disk.

    Returns the resolved `kind` on success; raises ValueError with a
    user-facing message on rejection. Three layers of defense, all run
    before the upload view writes the tmp file:

    1. Extension allow-list — the filename must end with one of the
       accepted suffixes (case-insensitive). Defeats casual uploads of
       the wrong type and any extension we never ingest.
    2. Magic-byte sniff — for kinds with a known signature (PDF today),
       the first bytes of the content must match. Defeats name-spoofing
       where an attacker renames a binary to .pdf to slip past (1).
    3. UTF-8 decode check — text and markdown have no portable magic
       bytes (they are arbitrary UTF-8), so for those we require the
       bytes to decode as UTF-8. A renamed binary fails here.
    """
    name = filename.lower()
    if not any(name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise ValueError(
            f"unsupported file type: {filename!r}; "
            f"accepted extensions: {sorted(ALLOWED_EXTENSIONS)}"
        )
    try:
        kind = detect_kind(filename, mime=None)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    sig = MAGIC_SIGNATURES.get(kind)
    if sig is not None:
        if not data.startswith(sig):
            raise ValueError(
                f"file {filename!r} claims to be a {kind} but its content "
                f"does not match the {kind!r} magic bytes; refusing upload"
            )
    else:
        # Text / markdown — verify it is decodable UTF-8 so a binary
        # payload renamed to .txt is rejected rather than producing
        # garbage chunks with U+FFFD replacements.
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                f"file {filename!r} is not valid UTF-8 text; refusing upload"
            ) from exc
    return kind


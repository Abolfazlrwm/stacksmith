"""Filesystem and log helpers for untrusted strings.

Owner names originate from the X-Docubot-Owner request header and are
persisted verbatim in the database, so they must never be used as a path
component verbatim. owner_dir_name() projects an owner onto a fixed
character class ([A-Za-z0-9._-], max 64 chars), which rules out path
traversal ("..", "/", "\\"), absolute-path escapes and empty components.
The closing re.fullmatch guard is a whitelist validation barrier: nothing
may leave this module as a path component unless it strictly matches the
allowed charset, which keeps the projection provable for taint analysis
(py/path-injection) as well as for humans.

Two distinct owners can project onto the same directory name only when
they normalize to the same slug; upload bytes are keyed by content
checksum, so such a collision yields identical bytes and is harmless.
"""
from __future__ import annotations

import re

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")
_SAFE_SLUG = re.compile(r"[A-Za-z0-9._-]{1,64}")

# Character class accepted in log-safe projections. It excludes every
# control character (CR, LF, ESC, ...) so a projected token cannot forge,
# split or re-colour log entries (py/log-injection).
_SAFE_LOG_TOKEN = re.compile(r"[A-Za-z0-9._-]{0,200}")


def owner_dir_name(owner: str | None) -> str:
    """Return a filesystem-safe directory name for an owner's uploads."""
    raw = (owner or "").strip()
    slug = _UNSAFE_CHARS.sub("_", raw).strip("._-")[:64]
    # Whitelist guard: only a slug that strictly matches the safe charset
    # may reach the filesystem; anything else collapses to "_shared".
    if not _SAFE_SLUG.fullmatch(slug):
        return "_shared"
    return slug


def log_safe(value: str | None, limit: int = 200) -> str:
    """Project untrusted text onto a whitelist charset for log entries.

    User-supplied strings (request headers, filenames, exception text
    that embeds a filename) must not reach the logging sink verbatim:
    CR/LF would let a caller forge log lines. CR and LF are escaped
    first (the newline-escape step), then every remaining character
    outside the whitelist is replaced with "_" and the result must
    strictly match the whitelist before it is returned; otherwise a
    fixed "<redacted>" token is used, so the returned string is always
    safe.
    """
    if value is None:
        return "<none>"
    # Escape line breaks before any further projection: \r\n and \n are
    # turned into a literal backslash-n so the text can neither split nor
    # forge a log entry. (\r is handled by the character projection below.)
    line_safe = value.replace("\r\n", "\\n").replace("\n", "\\n")
    projected = _UNSAFE_CHARS.sub("_", line_safe)[:limit]
    if not _SAFE_LOG_TOKEN.fullmatch(projected):
        return "<redacted>"
    return projected

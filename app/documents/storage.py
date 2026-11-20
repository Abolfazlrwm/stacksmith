"""Filesystem helpers for the upload volume.

Owner names originate from the X-Docubot-Owner request header and are
persisted verbatim in the database, so they must never be used as a path
component verbatim. owner_dir_name() projects an owner onto a fixed
character class ([A-Za-z0-9._-], max 64 chars), which rules out path
traversal ("..", "/", "\\"), absolute-path escapes and empty components.
Two distinct owners can project onto the same directory name only when
they normalize to the same slug; upload bytes are keyed by content
checksum, so such a collision yields identical bytes and is harmless.
"""
from __future__ import annotations

import re

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def owner_dir_name(owner: str | None) -> str:
    """Return a filesystem-safe directory name for an owner's uploads."""
    raw = (owner or "").strip()
    slug = _UNSAFE_CHARS.sub("_", raw).strip("._-")[:64]
    return slug or "_shared"

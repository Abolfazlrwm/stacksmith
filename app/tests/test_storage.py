"""Unit tests for documents.storage.owner_dir_name.

storage.py is deliberately dependency-free (no Django imports), so these
tests run without a database. They pin the security contract: the projected
directory name can never escape the upload root, no matter what the
X-Docubot-Owner header contained.
"""
from __future__ import annotations

import os
from pathlib import Path

from documents.storage import owner_dir_name

TRAVERSAL_PAYLOADS = [
    "../../etc",
    "../" * 10,
    "..",
    ".",
    "",
    None,
    "a/b/c",
    "..\\..\\win",
    "/etc/passwd",
    "C:\\Windows",
    "owner/../../other",
    "\x00\x01",
]


def test_owner_dir_name_cannot_escape_the_upload_root():
    for payload in TRAVERSAL_PAYLOADS:
        slug = owner_dir_name(payload)
        resolved = Path(os.path.normpath(Path("/data/uploads") / slug))
        assert str(resolved).startswith("/data/uploads/"), (payload, slug)
        # no component may traverse upward or be absolute
        assert ".." not in Path(slug).parts
        assert not slug.startswith("/")


def test_owner_dir_name_fixed_character_class():
    for payload in TRAVERSAL_PAYLOADS:
        slug = owner_dir_name(payload)
        assert slug and len(slug) <= 64
        assert all(c.isalnum() or c in "._-" for c in slug)


def test_owner_dir_name_preserves_ordinary_owners():
    assert owner_dir_name("alice") == "alice"
    assert owner_dir_name("acme.team-7") == "acme.team-7"
    assert owner_dir_name("  bob  ") == "bob"


def test_owner_dir_name_caps_length():
    assert owner_dir_name("x" * 200) == "x" * 64


def test_owner_dir_name_empty_falls_back_to_shared():
    assert owner_dir_name("") == "_shared"
    assert owner_dir_name(None) == "_shared"
    assert owner_dir_name("<>:@") == "_shared"  # every char unsafe -> stripped

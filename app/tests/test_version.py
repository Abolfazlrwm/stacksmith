"""Unit tests for the version plumbing — / reports the VERSION file.

Before v1.2.3 the version was hardcoded to '1.2.0' in config/urls.py
and drifted out of sync on every release (the v1.2.2 release shipped
with / reporting 1.2.0). The fix reads the VERSION file at import
time. These tests pin that the two stay in sync.

These tests do not depend on pytest-django (main's unit.yml installs
only pytest, not pytest-django). We build the request with
RequestFactory and call the view function directly — the same pattern
test_health uses for the readiness matrix.
"""
from __future__ import annotations

from pathlib import Path

from django.test import RequestFactory

import config.urls as config_urls


VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION"


def test_app_version_reads_version_file():
    # APP_VERSION is set at import time from the VERSION file at the
    # repo root. It must match the file contents (stripped).
    expected = VERSION_FILE.read_text().strip()
    assert config_urls.APP_VERSION == expected


def test_service_root_reports_real_version():
    # The health_root view must echo the real version, not a hardcoded one.
    expected = VERSION_FILE.read_text().strip()
    rf = RequestFactory()
    resp = config_urls.health_root(rf.get("/"))
    assert resp.status_code == 200
    import json
    body = json.loads(resp.content)
    assert body["service"] == "docubot"
    assert body["version"] == expected

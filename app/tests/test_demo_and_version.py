"""Tests for the demo route and the version sync across surfaces.

v1.2.5 introduces:

- /demo/ — serves the interactive product+code showcase HTML. This is
  the same file GitHub Pages publishes at
  https://abolfazlrwm.github.io/stacksmith/. The test pins that the
  route returns 200 with the right content type and that the file
  contains the product name (so a broken/empty deploy is caught).

- chat.html version drift fix — the brand badge in the chat UI now
  fetches the real version from / at runtime instead of a hardcoded
  "v1.2.0" that drifted on every release. The test pins that the
  badge is no longer hardcoded and that chat.html wires up the
  runtime fetch.

These tests, like the rest of the suite, do not depend on
pytest-django. They use Django's RequestFactory and the URL resolver
directly.
"""
from __future__ import annotations

from pathlib import Path

from django.test import RequestFactory
from django.urls import resolve

import config.urls as config_urls

VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION"
CHAT_HTML = Path(__file__).resolve().parents[1] / "templates" / "chat.html"
DEMO_HTML = Path(__file__).resolve().parents[1] / "templates" / "demo.html"


def test_demo_route_resolves():
    # The /demo/ URL must resolve to the TemplateView serving demo.html.
    match = resolve("/demo/")
    assert match.url_name == "demo-ui"


def test_demo_route_serves_showcase_html():
    # Hitting /demo/ returns 200 and the showcase HTML, not a 404 or
    # a redirect. We call the view directly to avoid spinning up the
    # full WSGI app (no staticfiles, no middleware).
    view = resolve("/demo/").func
    rf = RequestFactory()
    resp = view(rf.get("/demo/"))
    assert resp.status_code == 200
    body = resp.rendered_content if hasattr(resp, "rendered_content") else resp.content.decode()
    # The showcase mentions the product name and the version — a broken
    # or empty deploy would miss both.
    assert "docubot" in body
    assert "StackSmith" in body


def test_demo_html_file_exists_and_is_substantial():
    # Guard against accidentally deleting demo.html or committing an
    # empty file (the deploy workflow copies this file to Pages).
    assert DEMO_HTML.exists(), "app/templates/demo.html is missing"
    size = DEMO_HTML.stat().st_size
    # The showcase is ~50 KB; anything under 20 KB means it was truncated.
    assert size > 20_000, f"demo.html is suspiciously small: {size} bytes"


def test_chat_html_no_longer_hardcodes_version():
    # v1.2.0 hardcoded "v1.2.0" in the brand badge; it drifted on every
    # release. The fix fetches / at runtime. The badge element must
    # still exist (so the fetch has somewhere to write) but the
    # hardcoded version string must be gone.
    html = CHAT_HTML.read_text()
    assert 'id="app-version"' in html, "brand badge missing the app-version id"
    # The old hardcoded marker must be gone — this is the regression
    # we are pinning against.
    assert ">v1.2.0<" not in html, "chat.html still hardcodes v1.2.0 in the badge"
    assert ">v1.2." not in html, "chat.html still hardcodes a v1.2.x version in the badge"
    # The runtime fetch from / must be wired up.
    assert 'fetch("/"' in html, "chat.html does not fetch the version from /"


def test_version_file_is_not_drifted_against_changelog():
    # The VERSION file is the single source of truth. The CHANGELOG
    # must have a release entry for it so a reader can match the
    # running version to its notes.
    version = VERSION_FILE.read_text().strip()
    changelog = (Path(__file__).resolve().parents[2] / "CHANGELOG.md").read_text()
    assert f"[{version}]" in changelog, (
        f"VERSION is {version} but CHANGELOG.md has no [{version}] section"
    )


def test_root_endpoint_reports_version_that_demo_will_fetch():
    # The demo/chat UI fetches / to get the version. Make sure that
    # endpoint still returns the version key the UI reads.
    rf = RequestFactory()
    resp = config_urls.health_root(rf.get("/"))
    assert resp.status_code == 200
    import json
    body = json.loads(resp.content)
    assert "version" in body
    assert body["version"] == VERSION_FILE.read_text().strip()

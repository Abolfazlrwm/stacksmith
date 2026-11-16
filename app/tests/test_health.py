"""Unit tests for the health endpoints.

`live` is pure — the process being up. `ready` touches postgres and
redis; both dependencies are faked here so the status matrix (ok / fail
/ sentinel) can be proven without any infrastructure.
"""
from __future__ import annotations

import pytest
from django.test import Client

import health.views as hv


@pytest.fixture()
def client():
    return Client()


def test_live_is_always_ok(client):
    resp = client.get("/health/live/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


def test_service_root_reports_version(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"] == "docubot"


# ---------------------------------------------------------------------------
# readiness
# ---------------------------------------------------------------------------


class _FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, *args):
        pass

    def fetchone(self):
        return (1,)


class _FakeConn:
    def __init__(self, ok=True):
        self.ok = ok

    def cursor(self):
        if not self.ok:
            raise RuntimeError("postgres is down")
        return _FakeCursor()


class _FakeRedis:
    def __init__(self, ok=True):
        self.ok = ok

    def ping(self):
        if not self.ok:
            raise RuntimeError("redis is down")


@pytest.fixture()
def healthy(monkeypatch):
    monkeypatch.setattr(hv, "connection", _FakeConn(ok=True))
    monkeypatch.setattr(hv.redis, "from_url", lambda *a, **k: _FakeRedis(ok=True))
    monkeypatch.setattr("os.path.exists", lambda p: False)


def test_ready_all_ok(client, healthy):
    resp = client.get("/health/ready/")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"status": "ready", "checks": {"postgres": "ok", "redis": "ok"}}


def test_ready_postgres_down_is_503(client, monkeypatch):
    monkeypatch.setattr(hv, "connection", _FakeConn(ok=False))
    monkeypatch.setattr(hv.redis, "from_url", lambda *a, **k: _FakeRedis(ok=True))
    monkeypatch.setattr("os.path.exists", lambda p: False)
    resp = client.get("/health/ready/")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["postgres"].startswith("fail:")
    assert body["checks"]["redis"] == "ok"


def test_ready_redis_down_is_503(client, monkeypatch):
    monkeypatch.setattr(hv, "connection", _FakeConn(ok=True))
    monkeypatch.setattr(hv.redis, "from_url", lambda *a, **k: _FakeRedis(ok=False))
    monkeypatch.setattr("os.path.exists", lambda p: False)
    resp = client.get("/health/ready/")
    assert resp.status_code == 503
    assert resp.json()["checks"]["redis"].startswith("fail:")


def test_ready_sentinel_file_blocks_readiness(client, monkeypatch):
    """The canary-failure drill's sentinel: /tmp/break_ready forces 503."""
    monkeypatch.setattr("os.path.exists", lambda p: p == "/tmp/break_ready")
    resp = client.get("/health/ready/")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not_ready"
    assert "break_ready" in body["checks"]["sentinel"]

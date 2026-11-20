"""Health check views — liveness and readiness."""
import logging

import redis
from django.conf import settings
from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def live(request):
    """Liveness — the process is up."""
    return JsonResponse({"status": "alive"})


def ready(request):
    """Readiness — dependencies (postgres, redis) respond."""
    checks = {}

    # Sentinel file for canary-failure drills: if /tmp/break_ready exists,
    # /health/ready/ returns 503 so deploy.sh's canary check fails.
    # This simulates a bad release that passes liveness but fails readiness.
    import os
    if os.path.exists("/tmp/break_ready"):
        return JsonResponse(
            {"status": "not_ready", "checks": {"sentinel": "break_ready file present"}},
            status=503,
        )

    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        checks["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["postgres"] = f"fail: {exc}"

    try:
        client = redis.from_url(settings.CACHES["default"]["LOCATION"], socket_timeout=2)
        client.ping()
        checks["redis"] = "ok"
    except Exception:  # noqa: BLE001
        # Do not flow the exception text into the HTTP response; the detail
        # (which can include hostnames/URLs) stays in the server log only.
        logger.exception("readiness: redis check failed")
        checks["redis"] = "fail"

    ok = all(v == "ok" for v in checks.values())
    return JsonResponse(
        {"status": "ready" if ok else "not_ready", "checks": checks},
        status=200 if ok else 503,
    )

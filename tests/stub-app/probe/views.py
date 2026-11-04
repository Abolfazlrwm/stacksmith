import json

import redis as redis_lib
from django.conf import settings
from django.db import connection
from django.http import HttpResponse


def live(request):
    """Liveness: the process is up. No dependency checks."""
    return HttpResponse("ok")


def ready(request):
    """Readiness: postgres and redis answer. 503 on any failure."""
    checks = {}
    status = 200

    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "fail"
        status = 503

    try:
        client = redis_lib.from_url(settings.REDIS_URL, socket_timeout=2)
        client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "fail"
        status = 503

    return HttpResponse(
        json.dumps(checks), status=status, content_type="application/json"
    )

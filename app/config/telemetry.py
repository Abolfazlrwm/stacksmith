"""OpenTelemetry instrumentation — call once at startup."""
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry(service_name: str = "docubot"):
    """Configure OTel to export traces to Tempo over OTLP/HTTP.

    Returns True if telemetry was enabled, False if disabled.
    Instrumentation (Django, psycopg, redis, celery) is done lazily:
    each instrumentor is imported and applied only if its package is
    installed, so a missing optional dependency does not crash the app.
    """
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "")
    if not endpoint:
        return False  # telemetry disabled

    resource = Resource.create({
        "service.name": service_name,
        "service.version": os.environ.get("GIT_SHA", "dev"),
    })

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Auto-instrument — each import is guarded so a missing package
    # does not crash the app.
    try:
        from opentelemetry.instrumentation.django import DjangoInstrumentor
        DjangoInstrumentor().instrument()
    except ImportError:
        pass

    try:
        from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
        PsycopgInstrumentor().instrument()
    except ImportError:
        pass

    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        RedisInstrumentor().instrument()
    except ImportError:
        pass

    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        CeleryInstrumentor().instrument()
    except ImportError:
        pass

    return True

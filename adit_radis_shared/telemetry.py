"""OpenTelemetry configuration for ADIT, RADIS, and other openradx services.

This module sets up OpenTelemetry instrumentation for traces, metrics, and logs,
exporting to an OTLP-compatible backend (e.g., otel-collector -> OpenObserve).

Framework-specific auto-instrumentors (Django, Psycopg, requests, ...) are passed
in by the caller via `setup_opentelemetry(instrumentors=[...])` so this helper is
usable from non-Django consumers such as the radis-etl-ukb Dagster pipeline.

Telemetry is disabled if OTEL_EXPORTER_OTLP_ENDPOINT is not set.
"""

import logging
import os
import socket
from collections.abc import Iterable

logger = logging.getLogger(__name__)


_telemetry_active = False


def is_telemetry_active() -> bool:
    return _telemetry_active


def add_otel_logging_handler(logging_config: dict) -> None:
    """Add OpenTelemetry logging handler to a Django LOGGING dict.

    Call this after defining LOGGING in settings, only when is_telemetry_active() is True.
    This function is idempotent and safe to call on any valid Django logging config.
    """
    handlers = logging_config.setdefault("handlers", {})
    handlers.setdefault(
        "otel",
        {
            "level": "DEBUG",
            "class": "opentelemetry.sdk._logs.LoggingHandler",
        },
    )

    for logger_config in logging_config.get("loggers", {}).values():
        logger_handlers = logger_config.setdefault("handlers", [])
        if "otel" not in logger_handlers:
            logger_handlers.append("otel")

    root_handlers = logging_config.setdefault("root", {}).setdefault("handlers", [])
    if "otel" not in root_handlers:
        root_handlers.append("otel")


def _build_resource_attributes(service_name: str) -> dict[str, str]:
    """Build the OTel resource attribute dict for the current process.

    `service.component` is added when the SERVICE_COMPONENT env var is set,
    letting the observability overlay tag each container without needing to
    splice substrings into OTEL_RESOURCE_ATTRIBUTES per service. When TASK_SLOT
    holds a digit (Swarm interpolates `{{.Task.Slot}}` to the replica ordinal),
    it is appended as `-N` so replicas of the same service are distinguishable.
    Outside Swarm the literal template passes through unprocessed; the digit
    check drops it so dev signals stay clean.
    """
    attrs: dict[str, str] = {"service.name": service_name}
    if component := os.environ.get("SERVICE_COMPONENT"):
        slot = os.environ.get("TASK_SLOT", "")
        if slot.isdigit():
            component = f"{component}-{slot}"
        attrs["service.component"] = component
    return attrs


def setup_opentelemetry(instrumentors: Iterable[type] | None = None) -> None:
    """Initialize OpenTelemetry instrumentation for traces, metrics, and logs.

    Call once at application startup, before the host framework loads (e.g. before
    Django settings are imported, or before Dagster's code location is loaded).
    Configures trace, metric, and log exporters to send data to the OTLP endpoint
    (typically the openradx-observability otel-collector).

    Pass `instrumentors` as a sequence of OTel instrumentor classes (each providing
    a no-arg constructor and an `.instrument()` method) to enable framework-specific
    auto-instrumentation. For Django consumers (ADIT, RADIS) that is
    `[DjangoInstrumentor, PsycopgInstrumentor]`. For non-Django consumers (e.g. the
    radis-etl-ukb Dagster pipeline) pass `None` and optionally add HTTP-client
    instrumentors like `RequestsInstrumentor` so outbound calls propagate trace
    context to downstream services.

    If OTEL_EXPORTER_OTLP_ENDPOINT is not set, telemetry is disabled.
    """
    global _telemetry_active

    if _telemetry_active:
        logger.debug("OpenTelemetry already initialized; skipping")
        return

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logger.info("OTEL_EXPORTER_OTLP_ENDPOINT not set, telemetry disabled")
        return

    try:
        # Import OpenTelemetry modules only when needed.
        # Note: _logs and _log_exporter use underscore-prefixed modules because the
        # OTel Python logging SDK is still experimental. These are the official imports
        # recommended by the OTel Python documentation.
        from opentelemetry import metrics, trace
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk._logs import LoggerProvider
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        service_name = os.environ.get("OTEL_SERVICE_NAME")
        if not service_name:
            site_name = os.environ.get("SITE_NAME", "unknown")
            hostname = socket.gethostname()
            # Docker hostnames are like "web.local", "worker.local"
            role = hostname.split(".")[0] if "." in hostname else hostname
            service_name = f"{site_name}-{role}".lower().replace(" ", "-")

        # Create resource with service name and (optionally) component
        resource = Resource.create(_build_resource_attributes(service_name))

        # Setup tracing - otel-collector handles authentication to OpenObserve.
        # Construct full signal-specific URLs because passing endpoint to
        # the constructor bypasses the SDK's automatic path-appending logic.
        base = endpoint.rstrip("/")
        trace_exporter = OTLPSpanExporter(endpoint=f"{base}/v1/traces")
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
        trace.set_tracer_provider(tracer_provider)

        # Setup metrics
        metric_exporter = OTLPMetricExporter(endpoint=f"{base}/v1/metrics")
        metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=60000)
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)

        # Setup logging - export structured logs via OTLP
        log_exporter = OTLPLogExporter(endpoint=f"{base}/v1/logs")
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
        set_logger_provider(logger_provider)

        # Mark telemetry as active BEFORE running caller-provided instrumentors,
        # because some of them (notably DjangoInstrumentor) trigger framework
        # settings to load, which check is_telemetry_active() to decide whether
        # to add the OTel logging handler.
        _telemetry_active = True

        # Run caller-provided instrumentors. Each class is expected to expose a
        # no-arg constructor and an `.instrument()` method (the OTel
        # BaseInstrumentor contract). Imports of the instrumentor packages
        # therefore live with the caller, not here, so the package needs to
        # depend on `opentelemetry-instrumentation-django` etc. only when the
        # consumer is actually a Django app.
        for instrumentor_cls in instrumentors or ():
            instrumentor_cls().instrument()

        logger.info("OpenTelemetry initialized for service: %s", service_name)
    except Exception:
        logger.warning(
            "Failed to initialize OpenTelemetry, continuing without telemetry", exc_info=True
        )

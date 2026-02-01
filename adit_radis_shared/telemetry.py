"""OpenTelemetry configuration for ADIT and RADIS.

This module sets up OpenTelemetry instrumentation for traces, metrics, and logs,
exporting to an OTLP-compatible backend (e.g., otel-collector -> OpenObserve).

Telemetry is disabled if OTEL_EXPORTER_OTLP_ENDPOINT is not set.
"""

import logging
import os
import socket

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


def setup_opentelemetry() -> None:
    """Initialize OpenTelemetry instrumentation for traces, metrics, and logs.

    This function should be called once at application startup, before Django loads.
    It configures trace, metric, and log exporters to send data to the OTLP endpoint
    (typically otel-collector).

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
        from opentelemetry.instrumentation.django import DjangoInstrumentor
        from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
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

        # Create resource with service name
        resource = Resource.create({"service.name": service_name})

        # Setup tracing - otel-collector handles authentication to OpenObserve.
        # The OTLP HTTP exporters automatically append signal-specific paths
        # (e.g. /v1/traces) to the base endpoint.
        trace_exporter = OTLPSpanExporter(endpoint=endpoint)
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
        trace.set_tracer_provider(tracer_provider)

        # Setup metrics
        metric_exporter = OTLPMetricExporter(endpoint=endpoint)
        metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=60000)
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)

        # Setup logging - export structured logs via OTLP
        log_exporter = OTLPLogExporter(endpoint=endpoint)
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
        set_logger_provider(logger_provider)

        # Instrument Django
        DjangoInstrumentor().instrument()

        # Instrument psycopg (PostgreSQL)
        PsycopgInstrumentor().instrument()

        _telemetry_active = True
        logger.info("OpenTelemetry initialized for service: %s", service_name)
    except Exception:
        logger.warning(
            "Failed to initialize OpenTelemetry, continuing without telemetry", exc_info=True
        )

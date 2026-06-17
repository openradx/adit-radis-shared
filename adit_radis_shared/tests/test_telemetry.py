"""Unit tests for the telemetry module: the resource-attribute helper and the
pluggable-instrumentor contract used by setup_opentelemetry()."""

import importlib
from typing import Any

import pytest

from adit_radis_shared import telemetry
from adit_radis_shared.telemetry import _build_resource_attributes


def test_only_service_name_when_component_unset(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SERVICE_COMPONENT", raising=False)
    attrs = _build_resource_attributes("adit_prod")
    assert attrs == {"service.name": "adit_prod"}


def test_service_component_added_when_env_set(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SERVICE_COMPONENT", "mass_transfer_worker")
    attrs = _build_resource_attributes("adit_staging")
    assert attrs == {
        "service.name": "adit_staging",
        "service.component": "mass_transfer_worker",
    }


def test_empty_service_component_treated_as_unset(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SERVICE_COMPONENT", "")
    attrs = _build_resource_attributes("radis_prod")
    assert attrs == {"service.name": "radis_prod"}


def test_task_slot_appended_when_digit(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SERVICE_COMPONENT", "default_worker")
    monkeypatch.setenv("TASK_SLOT", "3")
    attrs = _build_resource_attributes("adit_prod")
    assert attrs == {
        "service.name": "adit_prod",
        "service.component": "default_worker-3",
    }


def test_task_slot_ignored_when_uninterpolated_template(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SERVICE_COMPONENT", "web")
    monkeypatch.setenv("TASK_SLOT", "{{.Task.Slot}}")
    attrs = _build_resource_attributes("adit_prod")
    assert attrs == {"service.name": "adit_prod", "service.component": "web"}


def test_task_slot_ignored_when_empty(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SERVICE_COMPONENT", "web")
    monkeypatch.setenv("TASK_SLOT", "")
    attrs = _build_resource_attributes("adit_prod")
    assert attrs == {"service.name": "adit_prod", "service.component": "web"}


def test_task_slot_alone_does_not_create_component(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SERVICE_COMPONENT", raising=False)
    monkeypatch.setenv("TASK_SLOT", "2")
    attrs = _build_resource_attributes("adit_prod")
    assert attrs == {"service.name": "adit_prod"}


# ----------------------------------------------------------------------------
# Pluggable-instrumentor contract
# ----------------------------------------------------------------------------
#
# These tests exercise the `instrumentors` parameter of setup_opentelemetry(),
# which lets non-Django consumers (e.g. radis-etl-ukb) reuse the helper without
# forcing the package to depend on opentelemetry-instrumentation-django and
# -psycopg. Django consumers install adit-radis-shared[django] and pass those
# instrumentor classes explicitly.


@pytest.fixture(autouse=True)
def _reset_telemetry_state(monkeypatch: pytest.MonkeyPatch):
    """Reset the module-level singleton flag between tests.

    setup_opentelemetry() short-circuits if `_telemetry_active` is True so that
    calling it twice in production is a no-op. We reset around each test so
    each scenario starts from a clean slate.
    """
    monkeypatch.setattr(telemetry, "_telemetry_active", False)
    yield
    monkeypatch.setattr(telemetry, "_telemetry_active", False)


class _RecordingInstrumentor:
    """Stand-in for an OTel BaseInstrumentor used to assert call ordering.

    Each instance appends (name, telemetry_active_flag_at_call_time) to a
    class-level list so tests can verify both invocation count and the
    invariant that `_telemetry_active` flips to True *before* any
    instrumentor runs.
    """

    calls: list[tuple[str, bool]] = []

    def __init__(self, name: str = "default") -> None:
        self.name = name

    def instrument(self) -> None:
        type(self).calls.append((self.name, telemetry.is_telemetry_active()))

    @classmethod
    def reset(cls) -> None:
        cls.calls = []


def _make_instrumentor_class(name: str) -> type[_RecordingInstrumentor]:
    """Create a one-off instrumentor class with a stable identifier so
    assertion output is legible when multiple instrumentors run in one test."""
    return type(
        f"Instrumentor_{name}",
        (_RecordingInstrumentor,),
        {"__init__": lambda self, _name=name: _RecordingInstrumentor.__init__(self, _name)},
    )


@pytest.fixture
def _otel_endpoint(monkeypatch: pytest.MonkeyPatch) -> str:
    """Provide a fake OTLP endpoint so setup_opentelemetry proceeds past the
    early-return guard. The exporters target the URL but never actually send
    during tests because the BatchSpan/LogProcessor flushes on shutdown only.
    """
    endpoint = "http://otel-collector.test:4318"
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", endpoint)
    monkeypatch.setenv("OTEL_SERVICE_NAME", "telemetry-test")
    return endpoint


def test_no_endpoint_short_circuits_without_touching_instrumentors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OTEL_EXPORTER_OTLP_ENDPOINT unset -> helper returns silently without
    instantiating any instrumentor. Production relies on this for dev/CI
    environments where no collector is reachable."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    _RecordingInstrumentor.reset()
    sentinel = _make_instrumentor_class("must_not_run")

    telemetry.setup_opentelemetry(instrumentors=[sentinel])

    assert telemetry.is_telemetry_active() is False
    assert _RecordingInstrumentor.calls == []


def test_default_call_runs_no_instrumentors(_otel_endpoint: str) -> None:
    """Calling setup_opentelemetry() with no instrumentors must still
    initialise the SDK (so the metrics API works) but must not run any
    framework-specific instrumentor — this is the radis-etl-ukb path."""
    _RecordingInstrumentor.reset()

    telemetry.setup_opentelemetry()

    assert telemetry.is_telemetry_active() is True
    assert _RecordingInstrumentor.calls == []


def test_explicit_instrumentors_are_invoked_in_order(_otel_endpoint: str) -> None:
    """Caller's instrumentors must be instantiated and .instrument()ed in the
    order provided. ADIT/RADIS rely on Django coming before Psycopg so the
    Psycopg hook sees the request span as its parent."""
    _RecordingInstrumentor.reset()
    first = _make_instrumentor_class("django_like")
    second = _make_instrumentor_class("psycopg_like")

    telemetry.setup_opentelemetry(instrumentors=[first, second])

    names = [name for name, _active in _RecordingInstrumentor.calls]
    assert names == ["django_like", "psycopg_like"]


def test_telemetry_active_flag_set_before_instrumentors_run(_otel_endpoint: str) -> None:
    """_telemetry_active must flip to True *before* any instrumentor runs.
    DjangoInstrumentor().instrument() triggers Django settings to import,
    which read is_telemetry_active() to decide whether to attach the OTel
    log handler — if the flag were still False at that point the handler
    would silently never be wired and prod logs would stop reaching
    OpenObserve."""
    _RecordingInstrumentor.reset()
    probe = _make_instrumentor_class("probe")

    telemetry.setup_opentelemetry(instrumentors=[probe])

    assert _RecordingInstrumentor.calls == [("probe", True)]


def test_instrumentor_exception_does_not_break_app(
    _otel_endpoint: str, caplog: pytest.LogCaptureFixture
) -> None:
    """An instrumentor that raises must be swallowed with a warning so the
    application boots even when telemetry is misconfigured. The outer
    try/except is precisely there so telemetry never breaks the host app."""

    class _Boom:
        def instrument(self) -> None:
            raise RuntimeError("instrumentor exploded")

    with caplog.at_level("WARNING", logger="adit_radis_shared.telemetry"):
        telemetry.setup_opentelemetry(instrumentors=[_Boom])

    assert any("Failed to initialize OpenTelemetry" in record.message for record in caplog.records)


def test_idempotent_second_call_is_noop(_otel_endpoint: str) -> None:
    """setup_opentelemetry called twice must not double-instrument. manage.py
    and asgi.py both call it (e.g. when running daphne via manage), so a
    double call must be a no-op to avoid duplicate Django/Psycopg spans."""
    _RecordingInstrumentor.reset()
    probe = _make_instrumentor_class("once_only")

    telemetry.setup_opentelemetry(instrumentors=[probe])
    telemetry.setup_opentelemetry(instrumentors=[probe])

    assert len(_RecordingInstrumentor.calls) == 1


def test_add_otel_logging_handler_attaches_to_all_loggers() -> None:
    """The logging-handler wiring is independent of SDK setup. After the helper
    runs every named logger and the root logger must reference the `otel`
    handler exactly once."""
    logging_config: dict[str, Any] = {
        "version": 1,
        "handlers": {"console": {"class": "logging.StreamHandler"}},
        "loggers": {
            "myapp": {"handlers": ["console"], "level": "INFO"},
            "django": {"handlers": ["console"], "level": "WARNING"},
        },
        "root": {"handlers": ["console"], "level": "ERROR"},
    }

    telemetry.add_otel_logging_handler(logging_config)

    assert "otel" in logging_config["handlers"]
    assert logging_config["loggers"]["myapp"]["handlers"] == ["console", "otel"]
    assert logging_config["loggers"]["django"]["handlers"] == ["console", "otel"]
    assert logging_config["root"]["handlers"] == ["console", "otel"]


def test_add_otel_logging_handler_is_idempotent() -> None:
    """Settings reloads (e.g. test runners overriding settings) must not
    duplicate the handler entries — duplicates would cause each log record to
    be emitted to OTel twice."""
    logging_config: dict[str, Any] = {
        "version": 1,
        "handlers": {"console": {"class": "logging.StreamHandler"}},
        "loggers": {"myapp": {"handlers": ["console"], "level": "INFO"}},
        "root": {"handlers": ["console"], "level": "ERROR"},
    }

    telemetry.add_otel_logging_handler(logging_config)
    telemetry.add_otel_logging_handler(logging_config)

    assert logging_config["loggers"]["myapp"]["handlers"].count("otel") == 1
    assert logging_config["root"]["handlers"].count("otel") == 1


def test_module_imports_without_django_extras() -> None:
    """The telemetry module must be importable without
    opentelemetry-instrumentation-django installed — this is what makes the
    extras split actually useful. Failing this test means we accidentally
    re-introduced a top-level Django-instrumentation import."""
    reloaded = importlib.reload(telemetry)
    assert hasattr(reloaded, "setup_opentelemetry")
    assert hasattr(reloaded, "add_otel_logging_handler")
    assert hasattr(reloaded, "is_telemetry_active")

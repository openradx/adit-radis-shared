"""Unit tests for the resource-attribute helper in telemetry.py."""

import pytest

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

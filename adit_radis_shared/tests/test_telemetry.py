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

"""Tests for ``common.forms``.

``BroadcastForm`` validates recipients against the User queryset; the
``SingleFilterFieldFormHelper`` builds a crispy-forms layout that mirrors the
current query params as hidden fields.
"""

import pytest
from crispy_forms.bootstrap import FieldWithButtons
from crispy_forms.layout import Hidden
from django import forms
from django.http import QueryDict

from adit_radis_shared.accounts.factories import UserFactory
from adit_radis_shared.common.forms import (
    BroadcastForm,
    RecipientsField,
    SingleFilterFieldFormHelper,
)


@pytest.mark.django_db
def test_broadcast_form_valid_with_existing_recipient():
    user = UserFactory.create()
    form = BroadcastForm(
        data={
            "recipients": [user.pk],
            "subject": "Hello",
            "message": "World",
        }
    )
    assert form.is_valid(), form.errors
    assert list(form.cleaned_data["recipients"]) == [user]


@pytest.mark.django_db
def test_broadcast_form_invalid_without_recipients():
    form = BroadcastForm(data={"subject": "Hi", "message": "There"})
    assert not form.is_valid()
    assert "recipients" in form.errors


@pytest.mark.django_db
def test_broadcast_form_recipients_widget_size_is_set():
    form = BroadcastForm()
    assert form.fields["recipients"].widget.attrs["size"] == 10


@pytest.mark.django_db
def test_recipients_field_label_includes_username_and_email():
    user = UserFactory.create(username="alice", email="alice@example.test")
    field = RecipientsField(queryset=type(user).objects.all())
    assert field.label_from_instance(user) == "alice <alice@example.test>"


def test_single_filter_helper_builds_field_with_buttons_layout():
    helper = SingleFilterFieldFormHelper(QueryDict(""), "status", button_label="Go")

    assert helper.form_method == "get"
    assert helper.disable_csrf is True
    # First layout entry is the FieldWithButtons wrapping the filter field.
    assert isinstance(helper.layout.fields[0], FieldWithButtons)


def test_single_filter_helper_carries_other_params_as_hidden_fields():
    params = QueryDict("status=PE&page=3&owner=7")
    helper = SingleFilterFieldFormHelper(params, "status")

    # The hidden-fields container is the second layout entry (a Div).
    hidden_container = helper.layout.fields[1]
    hidden_names = {f.name for f in hidden_container.fields if isinstance(f, Hidden)}

    # "status" is the active filter field and "page" is explicitly excluded;
    # only the remaining param should be carried over as a hidden input.
    assert "owner" in hidden_names
    assert "status" not in hidden_names
    assert "page" not in hidden_names


def test_single_filter_helper_render_adds_select_class_for_choice_field():
    from django.template import Context

    class _ChoiceFilterForm(forms.Form):
        status = forms.ChoiceField(choices=[("PE", "Pending")], required=False)

    helper = SingleFilterFieldFormHelper(QueryDict(""), "status")
    form = _ChoiceFilterForm()

    html = helper.render_layout(form, Context({}))

    # For a ChoiceField the helper injects the bootstrap select classes.
    assert "form-select" in helper._field.attrs["class"]
    assert html  # rendering produced output


def test_single_filter_helper_render_keeps_plain_class_for_char_field():
    from django.template import Context

    class _CharFilterForm(forms.Form):
        status = forms.CharField(required=False)

    helper = SingleFilterFieldFormHelper(QueryDict(""), "status")
    form = _CharFilterForm()

    helper.render_layout(form, Context({}))

    # A non-choice field keeps only the form-control sizing class.
    assert "form-select" not in helper._field.attrs["class"]

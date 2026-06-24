"""Behavioural tests for the view mixins in ``common.mixins``.

The mixins are exercised through small concrete view classes (test doubles)
combined with Django's ``RequestFactory``. Where a mixin needs real model data
(pagination / filtering) the ``example_app``'s ``ExampleJob`` model is used.
"""

from typing import Any

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import SuspiciousOperation
from django.test import RequestFactory
from django.views.generic import DetailView, ListView
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin

from adit_radis_shared.accounts.factories import AdminUserFactory
from adit_radis_shared.common.mixins import (
    HtmxOnlyMixin,
    LockedMixin,
    PageSizeSelectMixin,
    RelatedFilterMixin,
    RelatedPaginationMixin,
)
from example_project.example_app.factories import ExampleJobFactory
from example_project.example_app.filters import ExampleJobFilter
from example_project.example_app.models import ExampleJob
from example_project.example_app.tables import ExampleJobTable

# --- LockedMixin ------------------------------------------------------------


class _FakeSettings:
    """Stand-in for a concrete ``AppSettings`` singleton."""

    locked = False

    @classmethod
    def get(cls):
        return cls


class _LockedView(LockedMixin, ListView):
    model = ExampleJob
    settings_model = _FakeSettings  # type: ignore[assignment]
    section_name = "Example"
    template_name = "example_app/example_list.html"


@pytest.mark.django_db
def test_locked_mixin_passes_through_when_unlocked():
    _FakeSettings.locked = False
    request = RequestFactory().get("/")
    request.user = AnonymousUser()

    response = _LockedView.as_view()(request)
    assert response.status_code == 200


@pytest.mark.django_db
def test_locked_mixin_blocks_anonymous_get_with_locked_section():
    _FakeSettings.locked = True
    try:
        request = RequestFactory().get("/")
        request.user = AnonymousUser()

        response = _LockedView.as_view()(request)

        # When locked, the mixin short-circuits to the section_locked
        # TemplateView instead of the real list view. We assert on the
        # resolved template + context rather than rendered HTML because
        # section_locked.html extends "core/core_layout.html", a base template
        # only provided by the downstream apps (not example_project).
        assert response.status_code == 200
        assert "common/section_locked.html" in response.template_name
        assert response.context_data["section_name"] == "Example"
    finally:
        _FakeSettings.locked = False


@pytest.mark.django_db
def test_locked_mixin_raises_on_non_get_when_locked():
    _FakeSettings.locked = True
    try:
        request = RequestFactory().post("/")
        request.user = AnonymousUser()

        with pytest.raises(SuspiciousOperation):
            _LockedView.as_view()(request)
    finally:
        _FakeSettings.locked = False


@pytest.mark.django_db
def test_locked_mixin_allows_superuser_when_locked():
    _FakeSettings.locked = True
    try:
        admin = AdminUserFactory.create()
        request = RequestFactory().get("/")
        request.user = admin

        response = _LockedView.as_view()(request)
        # Superuser bypasses the lock and gets the real list view.
        assert response.status_code == 200
    finally:
        _FakeSettings.locked = False


# --- HtmxOnlyMixin ----------------------------------------------------------


class _HtmxOnlyView(HtmxOnlyMixin, ListView):
    model = ExampleJob
    template_name = "example_app/example_list.html"


@pytest.mark.django_db
def test_htmx_only_mixin_raises_without_htmx_header():
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    request.htmx = False  # type: ignore[attr-defined]

    with pytest.raises(SuspiciousOperation):
        _HtmxOnlyView.as_view()(request)


@pytest.mark.django_db
def test_htmx_only_mixin_passes_with_htmx_header():
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    request.htmx = True  # type: ignore[attr-defined]

    response = _HtmxOnlyView.as_view()(request)
    assert response.status_code == 200


# --- PageSizeSelectMixin ----------------------------------------------------


class _PageSizeView(PageSizeSelectMixin, ListView):
    model = ExampleJob
    template_name = "example_app/example_list.html"
    ordering = "id"  # avoids UnorderedObjectListWarning during pagination


def _context_after_get(view_cls, query="") -> dict[str, Any]:
    request = RequestFactory().get(f"/?{query}")
    request.user = AnonymousUser()
    view = view_cls()
    view.setup(request)
    # Run get() to set paginate_by, then build context the way Django does.
    view.object_list = view.get_queryset()
    view.get(request)
    return view, view.get_context_data()


@pytest.mark.django_db
def test_page_size_mixin_defaults_paginate_by():
    view, context = _context_after_get(_PageSizeView)
    assert view.paginate_by == 50
    assert context["page_sizes"] == [25, 50, 100, 250, 500]


@pytest.mark.django_db
def test_page_size_mixin_uses_per_page_query_param():
    view, _ = _context_after_get(_PageSizeView, query="per_page=25")
    assert view.paginate_by == 25


@pytest.mark.django_db
def test_page_size_mixin_caps_per_page_at_100():
    view, _ = _context_after_get(_PageSizeView, query="per_page=500")
    assert view.paginate_by == 100


@pytest.mark.django_db
def test_page_size_mixin_falls_back_on_non_integer():
    view, _ = _context_after_get(_PageSizeView, query="per_page=abc")
    assert view.paginate_by == 50


# --- RelatedPaginationMixin -------------------------------------------------


class _OwnerStub:
    pk = 1


class _RelatedPaginationView(RelatedPaginationMixin, DetailView):
    paginate_by = 2
    template_name = "example_app/example_list.html"

    def get_object(self, queryset=None):
        return _OwnerStub()

    def get_related_queryset(self):
        return ExampleJob.objects.all().order_by("id")


def _make_paginated_view(query=""):
    request = RequestFactory().get(f"/?{query}")
    request.user = AnonymousUser()
    view = _RelatedPaginationView()
    view.setup(request)
    view.object = view.get_object()
    return view


@pytest.mark.django_db
def test_related_pagination_paginates_related_queryset():
    ExampleJobFactory.create_batch(5)
    view = _make_paginated_view()
    context = view.get_context_data()

    assert context["paginator"].count == 5
    assert context["paginator"].num_pages == 3
    assert len(context["object_list"]) == 2  # paginate_by
    assert context["is_paginated"] is True
    assert context["page_obj"].number == 1


@pytest.mark.django_db
def test_related_pagination_respects_page_param():
    ExampleJobFactory.create_batch(5)
    view = _make_paginated_view(query="page=3")
    context = view.get_context_data()
    assert context["page_obj"].number == 3
    assert len(context["object_list"]) == 1  # last page remainder


@pytest.mark.django_db
def test_related_pagination_non_integer_page_falls_back_to_first():
    ExampleJobFactory.create_batch(3)
    view = _make_paginated_view(query="page=notanumber")
    context = view.get_context_data()
    assert context["page_obj"].number == 1


@pytest.mark.django_db
def test_related_pagination_out_of_range_page_returns_last():
    ExampleJobFactory.create_batch(3)
    view = _make_paginated_view(query="page=999")
    context = view.get_context_data()
    assert context["page_obj"].number == context["paginator"].num_pages


@pytest.mark.django_db
def test_related_pagination_default_get_related_queryset_raises():
    """The base implementation must be overridden by subclasses."""
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    view = RelatedPaginationMixin()
    view.request = request  # type: ignore[attr-defined]
    with pytest.raises(NotImplementedError):
        view.get_related_queryset()


# --- RelatedFilterMixin -----------------------------------------------------


class _RelatedFilterView(
    RelatedFilterMixin, SingleTableMixin, FilterView
):
    model = ExampleJob
    table_class = ExampleJobTable
    filterset_class = ExampleJobFilter
    template_name = "example_app/example_list.html"
    strict = False

    def get_filter_queryset(self):
        return ExampleJob.objects.all().order_by("id")


def _make_filter_view(query=""):
    request = RequestFactory().get(f"/?{query}")
    request.user = AnonymousUser()
    view = _RelatedFilterView()
    view.setup(request)
    view.object_list = view.get_filter_queryset()
    return view


@pytest.mark.django_db
def test_related_filter_unbound_returns_all():
    ExampleJobFactory.create_batch(3, status=ExampleJob.Status.PENDING)
    view = _make_filter_view()
    context = view.get_context_data()

    assert "filter" in context
    assert context["object_list"].count() == 3


@pytest.mark.django_db
def test_related_filter_applies_filterset_selection():
    ExampleJobFactory.create_batch(2, status=ExampleJob.Status.PENDING)
    ExampleJobFactory.create_batch(3, status=ExampleJob.Status.DONE)

    view = _make_filter_view(query="status=DO")
    context = view.get_context_data()

    statuses = {job.status for job in context["object_list"]}
    assert statuses == {ExampleJob.Status.DONE}
    assert context["object_list"].count() == 3


@pytest.mark.django_db
def test_related_filter_default_get_filter_queryset_raises():
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    view = RelatedFilterMixin()
    view.request = request  # type: ignore[attr-defined]
    with pytest.raises(NotImplementedError):
        view.get_filter_queryset()


@pytest.mark.django_db
def test_related_filter_kwargs_include_request_and_queryset():
    request = RequestFactory().get("/?status=PE")
    request.user = AnonymousUser()
    view = _RelatedFilterView()
    view.setup(request)

    kwargs = view.get_filterset_kwargs(ExampleJobFilter)
    assert kwargs["request"] is request
    assert kwargs["data"] is not None
    assert kwargs["queryset"] is not None

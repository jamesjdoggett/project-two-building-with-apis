from datetime import date
from unittest.mock import patch

import pytest
import requests
from django.db import IntegrityError, OperationalError, transaction
from django.db.models.query import QuerySet
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from .models import Entry
from .operations import save_entry

pytestmark = pytest.mark.django_db


def test_new_save_stores_authoritative_owned_snapshot_and_displays_defaults(
    viewer_client, viewer, provider_http, show_payload
):
    payload = {
        **show_payload,
        "genres": ["Drama", "Science-Fiction"],
        "language": "English",
        "ended": "2003-07-28",
        "status": "Ended",
    }
    get, upstream = provider_http
    upstream.json.return_value = payload
    response = viewer_client.post(reverse("shows:save", args=[180]))

    assert response.status_code == 302
    entry = Entry.objects.get()
    assert entry.owner == viewer
    assert entry.tvmaze_id == 180
    assert entry.title == "Firefly"
    assert entry.source_url == payload["url"]
    assert entry.summary == "A space adventure & friends."
    assert entry.genres == payload["genres"]
    assert entry.language == "English"
    assert entry.premiered == date(2002, 9, 20)
    assert entry.ended == date(2003, 7, 28)
    assert entry.provider_status == "Ended"
    assert entry.poster_url == payload["image"]["medium"]
    assert entry.provider_name == "TVmaze"
    assert entry.license_url == "https://creativecommons.org/licenses/by-sa/4.0/"
    assert (
        entry.summary_transformation == "Summaries converted from HTML to plain text."
    )
    assert entry.retrieved_at <= entry.created_at <= entry.updated_at
    get.assert_called_once_with(
        "https://api.tvmaze.com/shows/180",
        headers={"User-Agent": "ShowVault/0.1 (personal TV tracker)"},
        timeout=(10, 10),
        allow_redirects=False,
    )
    assert response.url == reverse("shows:detail", args=[entry.pk])
    detail = viewer_client.get(response.url)
    assert detail.status_code == 200
    for text in (
        b"Firefly",
        b"Planned",
        b"Unrated",
        b"No notes yet.",
        b"No bookmark set.",
        b"TVmaze",
        b"CC BY-SA 4.0",
        b"Summaries converted from HTML to plain text.",
    ):
        assert text in detail.content


def test_repeat_save_opens_unchanged_local_entry_without_http(
    viewer_client, viewer, provider_http
):
    entry = Entry.objects.create(
        owner=viewer,
        tvmaze_id=180,
        title="Original snapshot",
        source_url="https://www.tvmaze.com/shows/180",
        summary="Saved locally",
        retrieved_at=timezone.now(),
    )
    original = Entry.objects.values().get(pk=entry.pk)
    provider_http[0].side_effect = AssertionError("Repeat save must not use HTTP")

    response = viewer_client.post(reverse("shows:save", args=[180]))

    assert provider_http[0].call_count == 0
    assert response.status_code == 302
    assert response.url == reverse("shows:detail", args=[entry.pk])
    assert Entry.objects.count() == 1
    assert Entry.objects.values().get(pk=entry.pk) == original


@pytest.mark.parametrize(
    ("failure", "status", "message"),
    [
        ("timeout", 504, "timed out"),
        ("connection", 502, "Could not connect"),
        ("404", 400, "no longer available"),
        ("429", 503, "Wait 12 seconds"),
        ("500", 502, "unavailable"),
        ("503", 502, "unavailable"),
        ("302", 502, "unexpected response"),
        ("json", 502, "invalid data"),
        ("shape", 502, "invalid data"),
    ],
)
def test_failed_new_save_creates_no_row(
    viewer_client, provider_http, failure, status, message
):
    get, upstream = provider_http
    if failure == "timeout":
        get.side_effect = requests.Timeout()
    elif failure == "connection":
        get.side_effect = requests.ConnectionError()
    elif failure == "json":
        upstream.json.side_effect = requests.exceptions.JSONDecodeError("bad", "x", 0)
    elif failure == "shape":
        upstream.json.return_value = []
    else:
        upstream.status_code = int(failure)
        upstream.headers = {"Retry-After": "12"}
    response = viewer_client.post(reverse("shows:save", args=[180]))
    assert response.status_code == status
    assert message.encode() in response.content
    assert b"Try saving again" in response.content
    assert b"No new entry was saved" in response.content
    assert b"Traceback" not in response.content
    assert not Entry.objects.exists()
    get.assert_called_once()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", None),
        ("id", 181),
        ("id", True),
        ("id", "180"),
        ("id", 0),
        ("id", -1),
        ("id", 180.0),
        ("name", None),
        ("name", "  "),
        ("name", []),
        ("url", None),
        ("url", "https://evil.example/shows/180"),
        ("url", "javascript:alert(1)"),
        ("summary", []),
        ("genres", "Drama"),
        ("genres", [1]),
        ("language", []),
        ("language", False),
        ("status", {}),
        ("status", 0),
        ("premiered", "invalid"),
        ("premiered", False),
        ("ended", "2026-02-30"),
        ("ended", 42),
        ("image", []),
        ("image", {"medium": "javascript:alert(1)"}),
    ],
)
def test_invalid_detail_fields_fail_atomically(
    viewer_client, provider_http, show_payload, field, value
):
    provider_http[1].json.return_value = {**show_payload, field: value}
    response = viewer_client.post(reverse("shows:save", args=[180]))
    assert response.status_code == 502
    assert b"invalid data" in response.content
    assert not Entry.objects.exists()


@pytest.mark.parametrize("explicit_nulls", [False, True])
def test_missing_optional_detail_fields_save_with_local_placeholders(
    viewer_client, provider_http, explicit_nulls
):
    payload = {"id": 180, "name": "Mystery", "url": "https://www.tvmaze.com/shows/180"}
    if explicit_nulls:
        payload.update(
            dict.fromkeys(
                [
                    "summary",
                    "genres",
                    "language",
                    "status",
                    "premiered",
                    "ended",
                    "image",
                ]
            )
        )
    provider_http[1].json.return_value = payload
    response = viewer_client.post(reverse("shows:save", args=[180]))
    assert response.status_code == 302
    entry = Entry.objects.get()
    assert entry.genres == []
    assert entry.language == entry.provider_status == entry.poster_url == ""
    assert entry.premiered is entry.ended is None
    page = viewer_client.get(response.url)
    assert b"Unknown" in page.content
    assert b"No summary available." in page.content
    assert b'src="/static/shows/poster-placeholder.svg"' in page.content


@pytest.mark.parametrize(
    "field",
    [
        "owner",
        "owner_id",
        "title",
        "summary",
        "source_url",
        "poster_url",
        "url",
        "tvmaze_id",
        "rating",
        "notes",
        "watch_status",
        "retrieved_at",
    ],
)
def test_save_rejects_forged_fields_before_http(viewer_client, provider_http, field):
    response = viewer_client.post(reverse("shows:save", args=[180]), {field: "forged"})
    assert response.status_code == 400
    assert b"no extra fields" in response.content
    assert not Entry.objects.exists()
    provider_http[0].assert_not_called()


def test_save_rejects_json_and_query_overrides(viewer_client, provider_http):
    url = reverse("shows:save", args=[180])
    assert (
        viewer_client.post(
            url, {"owner": 1}, content_type="application/json"
        ).status_code
        == 400
    )
    assert (
        viewer_client.post(url + "?source_url=https://evil.example/").status_code == 400
    )
    assert not Entry.objects.exists()
    provider_http[0].assert_not_called()


@pytest.mark.parametrize("show_id", [0, -1, True, 1.5, "180", None, 2**63])
def test_invalid_save_ids_are_rejected_without_http(viewer, provider_http, show_id):
    with pytest.raises(ValueError, match="positive whole-number"):
        save_entry(viewer, show_id)
    assert not Entry.objects.exists()
    provider_http[0].assert_not_called()


@pytest.mark.parametrize(
    "path",
    [
        "/discover/0/save/",
        "/discover/-1/save/",
        "/discover/1.5/save/",
        "/discover/9223372036854775808/save/",
    ],
)
def test_invalid_save_urls_fail_safely(viewer_client, provider_http, path):
    assert viewer_client.post(path).status_code in {400, 404}
    assert not Entry.objects.exists()
    provider_http[0].assert_not_called()


def test_two_owners_save_independent_snapshots(
    viewer_client, viewer, django_user_model, provider_http, show_payload, monkeypatch
):
    from . import tvmaze

    provider_http[1].json.return_value = show_payload
    first = viewer_client.post(reverse("shows:save", args=[180]))
    original = Entry.objects.values().get(owner=viewer)
    other = django_user_model.objects.create_user(username="other")
    viewer_client.force_login(other)
    monkeypatch.setattr(tvmaze, "request_gate", tvmaze.RequestGate())
    provider_http[1].json.return_value = {**show_payload, "name": "Different snapshot"}
    second = viewer_client.post(reverse("shows:save", args=[180]))
    assert first.status_code == second.status_code == 302
    assert first.url != second.url
    assert Entry.objects.count() == 2
    assert Entry.objects.get(owner=other).title == "Different snapshot"
    assert Entry.objects.values().get(owner=viewer) == original
    assert provider_http[0].call_count == 2


@pytest.mark.parametrize("privilege", ["ordinary", "staff", "superuser"])
def test_library_and_detail_are_owner_scoped_even_for_staff(
    viewer_client, entry_factory, django_user_model, provider_http, privilege
):
    owned = entry_factory(title="Private owned show")
    other = django_user_model.objects.create_user(
        username="other",
        is_staff=privilege != "ordinary",
        is_superuser=privilege == "superuser",
    )
    foreign = entry_factory(owner=other, title="Other secret show")
    provider_http[0].side_effect = AssertionError("Local pages must not use HTTP")
    for account, visible, hidden in (
        (owned.owner, owned, foreign),
        (other, foreign, owned),
    ):
        viewer_client.force_login(account)
        page = viewer_client.get(reverse("shows:library"))
        assert visible.title.encode() in page.content
        assert hidden.title.encode() not in page.content
        assert (
            viewer_client.get(reverse("shows:detail", args=[visible.pk])).status_code
            == 200
        )
        assert (
            viewer_client.get(reverse("shows:detail", args=[hidden.pk])).status_code
            == 404
        )
        assert (
            viewer_client.get(reverse("shows:detail", args=[999999])).status_code == 404
        )
        duplicate = viewer_client.post(reverse("shows:save", args=[180]))
        assert duplicate.url == reverse("shows:detail", args=[visible.pk])
    provider_http[0].assert_not_called()


def test_pagination_uses_only_owned_entries_and_stable_recent_order(
    viewer_client, entry_factory, django_user_model, provider_http
):
    entries = [entry_factory(tvmaze_id=i + 1, title=f"Show {i}") for i in range(21)]
    # Tie creation times so ordering must use the primary-key tiebreaker.
    Entry.objects.update(created_at=entries[0].created_at)
    other = django_user_model.objects.create_user(username="other")
    entry_factory(owner=other, title="Hidden entry")
    provider_http[0].side_effect = AssertionError("Local pagination must not use HTTP")
    url = reverse("shows:library")
    first = viewer_client.get(url)
    second = viewer_client.get(url, {"page": 2})
    assert list(first.context["page_obj"]) == entries[:0:-1]
    assert list(second.context["page_obj"]) == entries[:1]
    assert first.context["page_obj"].paginator.count == 21
    assert b"Next</a>" in first.content
    assert b"Previous</a>" not in first.content
    assert b"Previous</a>" in second.content
    assert b"Next</a>" not in second.content
    assert b"Page 2 of 2" in second.content
    for value, expected in [("bad", 1), ("0", 2), ("-1", 2), ("999", 2)]:
        response = viewer_client.get(url, {"page": value})
        assert response.context["page_obj"].number == expected
    provider_http[0].assert_not_called()


def test_empty_library_and_root_destination(viewer_client, provider_http):
    response = viewer_client.get(reverse("shows:home"))
    assert response.status_code == 302
    assert response.url == reverse("shows:library")
    page = viewer_client.get(response.url)
    assert b"Your library is empty" in page.content
    assert b"Discover shows" in page.content
    provider_http[0].assert_not_called()


def test_local_metadata_is_escaped_and_failed_posters_have_fallback(
    viewer_client, entry_factory, provider_http
):
    entry = entry_factory(
        title='<script>alert("title")</script>',
        summary='<img src=x onerror="alert(1)">',
        poster_url="https://static.tvmaze.com/unavailable.jpg",
    )
    provider_http[0].side_effect = AssertionError("Local pages must not use HTTP")
    for url in [reverse("shows:library"), reverse("shows:detail", args=[entry.pk])]:
        response = viewer_client.get(url)
        assert response.status_code == 200
        assert b"&lt;script&gt;" in response.content
        assert b"&lt;img" in response.content
        assert b"<script>alert" not in response.content
        assert b"<img src=x onerror=" not in response.content
        assert (
            b'data-fallback="/static/shows/poster-placeholder.svg"' in response.content
        )
        assert b"https://creativecommons.org/licenses/by-sa/4.0/" in response.content
    provider_http[0].assert_not_called()


def test_saved_discovery_indicators_are_owner_scoped(
    viewer_client, entry_factory, django_user_model, provider_http, show_payload
):
    entry_factory()
    other = django_user_model.objects.create_user(username="other")
    entry_factory(owner=other, tvmaze_id=181)
    provider_http[1].json.return_value = [
        {"show": show_payload},
        {"show": {**show_payload, "id": 181}},
    ]
    response = viewer_client.get(reverse("shows:discover"), {"q": "Firefly"})
    assert response.context["saved_ids"] == {180}
    assert response.content.count(b">Saved</span>") == 1
    assert b"Open saved entry" in response.content
    assert b"Save to library" in response.content
    assert b'action="/discover/180/save/"' in response.content
    assert b'action="/discover/181/save/"' in response.content


def test_new_endpoints_enforce_authentication_methods_and_csrf(
    client, viewer_client, viewer, entry_factory, provider_http, show_payload
):
    entry = entry_factory(tvmaze_id=181)
    for url in [
        reverse("shows:library"),
        reverse("shows:detail", args=[entry.pk]),
        reverse("shows:save", args=[180]),
    ]:
        anonymous = Client()
        assert anonymous.get(url).url.startswith(reverse("login") + "?next=")
    save_url = reverse("shows:save", args=[180])
    for method in ("get", "put", "patch", "delete", "head"):
        assert getattr(viewer_client, method)(save_url).status_code == 405
    assert (
        viewer_client.post(reverse("shows:detail", args=[entry.pk])).status_code == 405
    )
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(viewer)
    assert csrf_client.post(save_url).status_code == 403
    csrf_client.get(reverse("shows:discover"))
    provider_http[0].assert_not_called()
    provider_http[1].json.return_value = show_payload
    response = csrf_client.post(
        save_url, {"csrfmiddlewaretoken": csrf_client.cookies["csrftoken"].value}
    )
    assert response.status_code == 302
    assert Entry.objects.count() == 2


def test_database_enforces_unique_owner_and_positive_show_id(entry_factory):
    entry_factory()
    with pytest.raises(IntegrityError), transaction.atomic():
        entry_factory()
    with pytest.raises(IntegrityError), transaction.atomic():
        entry_factory(tvmaze_id=0)
    assert Entry.objects.count() == 1


def test_unique_collision_recovers_winner_without_overwriting_snapshot(
    viewer, entry_factory, provider_http, show_payload
):
    winner = entry_factory(title="Winning snapshot")
    original = Entry.objects.values().get(pk=winner.pk)
    provider_http[1].json.return_value = show_payload
    original_get = QuerySet.get
    calls = []

    def get_during_race(queryset, *args, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise Entry.DoesNotExist
        return original_get(queryset, *args, **kwargs)

    # Model the two stale reads before an INSERT hits the real unique constraint.
    with (
        patch.object(QuerySet, "first", return_value=None),
        patch.object(QuerySet, "get", get_during_race),
    ):
        entry, created = save_entry(viewer, 180)
    assert len(calls) == 2
    assert entry.pk == winner.pk and not created
    assert Entry.objects.count() == 1
    assert Entry.objects.values().get(pk=entry.pk) == original


def test_sqlite_write_lock_returns_actionable_retry_without_partial_row(
    viewer_client, provider_http, show_payload
):
    provider_http[1].json.return_value = show_payload
    with patch.object(
        QuerySet, "get_or_create", side_effect=OperationalError("database is locked")
    ):
        response = viewer_client.post(reverse("shows:save", args=[180]))
    assert response.status_code == 503
    assert b"library is busy" in response.content
    assert b"Traceback" not in response.content
    assert not Entry.objects.exists()


def test_discovery_and_save_share_request_budget(
    viewer_client, provider_http, show_payload, monkeypatch
):
    from . import tvmaze

    monkeypatch.setattr(tvmaze.time, "monotonic", lambda: 100.0)
    assert (
        viewer_client.get(reverse("shows:discover"), {"q": "Firefly"}).status_code
        == 200
    )
    provider_http[1].json.return_value = show_payload
    response = viewer_client.post(reverse("shows:save", args=[180]))
    assert response.status_code == 503
    assert b"Wait 1 second" in response.content
    assert not Entry.objects.exists()
    provider_http[0].assert_called_once()


def test_forged_duplicate_input_does_not_change_existing_entry(
    viewer_client, entry_factory, provider_http
):
    entry = entry_factory()
    original = Entry.objects.values().get(pk=entry.pk)
    response = viewer_client.post(
        reverse("shows:save", args=[180]), {"title": "Replacement"}
    )
    assert response.status_code == 400
    assert Entry.objects.values().get(pk=entry.pk) == original
    provider_http[0].assert_not_called()


def test_sqlite_lock_after_competing_commit_returns_winner(
    viewer, entry_factory, provider_http, show_payload
):
    provider_http[1].json.return_value = show_payload
    winner = None

    def competing_write(**kwargs):
        nonlocal winner
        winner = entry_factory(title="Winner")
        raise OperationalError("database table is locked")

    with patch.object(QuerySet, "get_or_create", side_effect=competing_write):
        entry, created = save_entry(viewer, 180)
    assert not created
    assert entry.pk == winner.pk
    assert entry.title == "Winner"
    assert Entry.objects.count() == 1

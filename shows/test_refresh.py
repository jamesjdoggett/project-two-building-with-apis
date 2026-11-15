from unittest.mock import patch

import pytest
import requests
from django.urls import reverse

from . import tvmaze
from .models import Entry
from .operations import refresh_entry

pytestmark = pytest.mark.django_db


def test_refresh_preserves_personal_edit_during_http(viewer, entry_factory):
    entry = entry_factory(notes="Before", rating=1)
    created = entry.created_at

    def fetch(show_id):
        assert show_id == entry.tvmaze_id
        Entry.objects.filter(pk=entry.pk).update(
            notes="Edited during HTTP",
            rating=10,
            watch_status="completed",
            last_season=0,
            last_episode=1,
        )
        return {"title": "Refreshed title", "summary": "New summary"}

    with patch("shows.operations.get_show", side_effect=fetch):
        refreshed = refresh_entry(viewer, entry.pk)

    entry.refresh_from_db()
    assert entry.title == "Refreshed title"
    assert entry.summary == "New summary"
    assert entry.notes == refreshed.notes == "Edited during HTTP"
    assert entry.rating == 10
    assert entry.watch_status == "completed"
    assert (entry.last_season, entry.last_episode) == (0, 1)
    assert entry.created_at == created


def test_refresh_deleted_during_http_returns_404_without_resurrection(
    viewer_client, entry_factory
):
    entry = entry_factory()
    pk = entry.pk

    def fetch(show_id):
        Entry.objects.filter(pk=pk).delete()
        return {"title": "Too late"}

    viewer_client.raise_request_exception = False
    with patch("shows.operations.get_show", side_effect=fetch):
        response = viewer_client.post(reverse("shows:refresh", args=[pk]))
    assert response.status_code == 404
    assert not Entry.objects.filter(pk=pk).exists()


def test_refresh_replaces_snapshot_only_for_owner(
    viewer_client, entry_factory, django_user_model, provider_http, show_payload
):
    entry = entry_factory(
        rating=9,
        notes="Private\nnotes",
        watch_status="paused",
        last_season=2,
        last_episode=3,
    )
    other = entry_factory(owner=django_user_model.objects.create_user(username="other"))
    before = Entry.objects.values().get(pk=entry.pk)
    other_before = Entry.objects.values().get(pk=other.pk)
    payload = {
        **show_payload,
        "name": "New title",
        "genres": ["Drama"],
        "language": "English",
        "status": "Ended",
        "ended": "2003-07-28",
    }
    provider_http[1].json.return_value = payload
    response = viewer_client.post(reverse("shows:refresh", args=[entry.pk]))
    assert response.status_code == 302
    after = Entry.objects.values().get(pk=entry.pk)
    expected = tvmaze.parse_show(payload)
    assert after["title"] == expected.title
    assert after["summary"] == expected.summary
    assert after["genres"] == ["Drama"]
    assert after["language"] == "English"
    assert after["provider_status"] == "Ended"
    assert str(after["ended"]) == "2003-07-28"
    assert str(after["premiered"]) == "2002-09-20"
    assert after["poster_url"] == expected.poster_url
    assert after["source_url"] == expected.source_url
    assert after["retrieved_at"] > before["retrieved_at"]
    assert after["updated_at"] > before["updated_at"]
    changed = {
        "title",
        "summary",
        "genres",
        "language",
        "provider_status",
        "ended",
        "premiered",
        "poster_url",
        "source_url",
        "retrieved_at",
        "updated_at",
    }
    assert {k: v for k, v in after.items() if k not in changed} == {
        k: v for k, v in before.items() if k not in changed
    }
    assert Entry.objects.values().get(pk=other.pk) == other_before
    provider_http[0].assert_called_once()


@pytest.mark.parametrize(
    "failure,status,message",
    [
        ("timeout", 504, "timed out"),
        ("connection", 502, "Could not connect"),
        ("404", 502, "no longer available"),
        ("429", 503, "Wait 12 seconds"),
        ("500", 502, "unavailable"),
        ("503", 502, "unavailable"),
        ("302", 502, "unexpected response"),
        ("json", 502, "invalid data"),
        ("shape", 502, "invalid data"),
        ("id", 502, "invalid data"),
        ("name", 502, "invalid data"),
        ("genres", 502, "invalid data"),
        ("ended", 502, "invalid data"),
        ("image", 502, "invalid data"),
        ("url", 502, "invalid data"),
        ("language", 502, "invalid data"),
    ],
)
def test_refresh_failure_preserves_every_saved_field(
    viewer_client, entry_factory, provider_http, show_payload, failure, status, message
):
    entry = entry_factory(
        rating=8, notes="Keep", watch_status="completed", last_season=0, last_episode=1
    )
    before = Entry.objects.values().get(pk=entry.pk)
    get, upstream = provider_http
    payload = {**show_payload, "name": "Must not partially persist"}
    upstream.json.return_value = payload
    if failure == "timeout":
        get.side_effect = requests.Timeout()
    elif failure == "connection":
        get.side_effect = requests.ConnectionError()
    elif failure == "json":
        upstream.json.side_effect = requests.exceptions.JSONDecodeError("bad", "x", 0)
    elif failure == "shape":
        upstream.json.return_value = []
    elif failure.isdigit():
        upstream.status_code = int(failure)
        upstream.headers = {"Retry-After": "12"}
    else:
        payload[failure] = {
            "id": 181,
            "name": "",
            "genres": "bad",
            "ended": "bad",
            "image": [],
            "url": "javascript:x",
            "language": [],
        }[failure]
    response = viewer_client.post(reverse("shows:refresh", args=[entry.pk]))
    assert response.status_code == status
    assert message.encode() in response.content
    assert b"Traceback" not in response.content
    assert Entry.objects.values().get(pk=entry.pk) == before


def test_refresh_missing_optional_fields_is_valid(
    viewer_client, entry_factory, provider_http
):
    entry = entry_factory()
    provider_http[1].json.return_value = {
        "id": 180,
        "name": "Minimal",
        "url": "https://www.tvmaze.com/shows/180",
    }
    assert (
        viewer_client.post(reverse("shows:refresh", args=[entry.pk])).status_code == 302
    )
    entry.refresh_from_db()
    assert entry.title == "Minimal"
    assert entry.poster_url == ""
    assert entry.genres == []
    assert entry.premiered is None


def test_discovery_save_refresh_share_throttle(
    viewer_client, entry_factory, provider_http, monkeypatch
):
    monkeypatch.setattr(tvmaze.time, "monotonic", lambda: 100.0)
    entry = entry_factory()
    viewer_client.get(reverse("shows:discover"), {"q": "Firefly"})
    assert viewer_client.post(reverse("shows:save", args=[181])).status_code == 503
    assert (
        viewer_client.post(reverse("shows:refresh", args=[entry.pk])).status_code == 503
    )
    provider_http[0].assert_called_once()

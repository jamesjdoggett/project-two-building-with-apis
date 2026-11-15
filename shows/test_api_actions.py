from unittest.mock import patch

import pytest
import requests
from django.test import Client
from django.urls import reverse

from .models import Entry
from .operations import SaveBusy
from .personal import PERSONAL_FIELDS
from .tvmaze import ProviderError

pytestmark = pytest.mark.django_db


def test_api_refresh_preserves_edit_during_http_and_other_snapshot(
    viewer_client, entry_factory, django_user_model
):
    entry = entry_factory(rating=1, notes="Before")
    other = entry_factory(owner=django_user_model.objects.create_user(username="other"))
    other_before = Entry.objects.values().get(pk=other.pk)
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
        response = viewer_client.post(f"/api/entries/{entry.pk}/refresh/")
    assert response.status_code == 200
    data = response.json()
    entry.refresh_from_db()
    assert data["title"] == entry.title == "Refreshed title"
    assert data["notes"] == entry.notes == "Edited during HTTP"
    assert data["rating"] == 10
    assert data["watch_status"] == "completed"
    assert (data["last_season"], data["last_episode"]) == (0, 1)
    assert entry.created_at == created
    assert Entry.objects.values().get(pk=other.pk) == other_before


def test_api_delete_is_immediate_private_and_resave_starts_fresh(
    viewer_client, entry_factory, django_user_model, provider_http, show_payload
):
    entry = entry_factory(
        rating=9, notes="Erase", watch_status="completed", last_season=2, last_episode=3
    )
    other = entry_factory(owner=django_user_model.objects.create_user(username="other"))
    other_before = Entry.objects.values().get(pk=other.pk)
    response = viewer_client.delete(f"/api/entries/{entry.pk}/")
    assert response.status_code == 204
    assert response.content == b""
    assert not Entry.objects.filter(pk=entry.pk).exists()
    assert Entry.objects.values().get(pk=other.pk) == other_before
    provider_http[0].assert_not_called()
    provider_http[1].json.return_value = show_payload
    response = viewer_client.post(
        "/api/entries/", {"tvmaze_id": 180}, content_type="application/json"
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] != entry.pk
    assert (
        data["rating"],
        data["notes"],
        data["watch_status"],
        data["last_season"],
        data["last_episode"],
    ) == (None, "", "planned", None, None)


def test_refresh_replaces_complete_validated_snapshot(
    viewer_client, entry_factory, provider_http, show_payload
):
    entry = entry_factory(rating=8, notes="Keep", last_season=0, last_episode=1)
    before = Entry.objects.values().get(pk=entry.pk)
    provider_http[1].json.return_value = {
        **show_payload,
        "name": "Updated",
        "genres": ["Drama"],
        "language": "English",
        "status": "Ended",
        "ended": "2003-07-28",
    }
    response = viewer_client.post(reverse("api:entry-refresh", args=[entry.pk]))
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated"
    assert data["summary"] == "A space adventure & friends."
    assert data["genres"] == ["Drama"]
    assert data["language"] == "English"
    assert data["provider_status"] == "Ended"
    assert data["premiered"] == "2002-09-20"
    assert data["ended"] == "2003-07-28"
    assert data["source_url"] == show_payload["url"]
    assert data["poster_url"] == show_payload["image"]["medium"]
    after = Entry.objects.values().get(pk=entry.pk)
    assert after["retrieved_at"] > before["retrieved_at"]
    assert after["updated_at"] > before["updated_at"]
    for name in [
        *PERSONAL_FIELDS,
        "owner_id",
        "tvmaze_id",
        "created_at",
        "provider_name",
        "license_url",
        "summary_transformation",
    ]:
        assert after[name] == before[name]


@pytest.mark.parametrize(
    "failure,status",
    [
        ("timeout", 504),
        ("connection", 502),
        ("404", 502),
        ("429", 503),
        ("500", 502),
        ("503", 502),
        ("302", 502),
        ("json", 502),
        ("shape", 502),
        ("id", 502),
        ("name", 502),
        ("genres", 502),
        ("ended", 502),
        ("image", 502),
        ("url", 502),
        ("language", 502),
    ],
)
def test_refresh_failures_are_structured_and_preserve_every_field(
    viewer_client, entry_factory, provider_http, show_payload, failure, status
):
    entry = entry_factory(
        rating=9,
        notes="Private",
        watch_status="completed",
        last_season=0,
        last_episode=1,
    )
    before = Entry.objects.values().get(pk=entry.pk)
    get, upstream = provider_http
    payload = {**show_payload, "name": "Must not partially persist"}
    upstream.json.return_value = payload
    if failure == "timeout":
        get.side_effect = requests.Timeout("secret provider HTML")
    elif failure == "connection":
        get.side_effect = requests.ConnectionError("secret provider HTML")
    elif failure == "json":
        upstream.json.side_effect = requests.exceptions.JSONDecodeError(
            "secret", "<html>", 0
        )
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
            "url": "javascript:secret",
            "language": [],
        }[failure]
    response = viewer_client.post(reverse("api:entry-refresh", args=[entry.pk]))
    assert response.status_code == status
    assert response.json()["detail"]
    assert all(
        word not in str(response.json()) for word in ["secret", "<html>", "Traceback"]
    )
    if status == 503:
        assert response.json()["retry_after"] == 12
        assert response["Retry-After"] == "12"
    assert Entry.objects.values().get(pk=entry.pk) == before


@pytest.mark.parametrize(
    "failure", [SaveBusy("secret lock details"), ProviderError("secret upstream body")]
)
def test_refresh_internal_failures_do_not_leak(viewer_client, entry_factory, failure):
    entry = entry_factory()
    before = Entry.objects.values().get(pk=entry.pk)
    with patch("shows.api.refresh_entry", side_effect=failure):
        response = viewer_client.post(reverse("api:entry-refresh", args=[entry.pk]))
    assert response.status_code == (503 if isinstance(failure, SaveBusy) else 502)
    assert "secret" not in str(response.json())
    assert Entry.objects.values().get(pk=entry.pk) == before


def test_provider_missing_show_creation_400_refresh_502(
    viewer_client, entry_factory, provider_http, monkeypatch
):
    from . import tvmaze

    entry = entry_factory()
    provider_http[1].status_code = 404
    assert (
        viewer_client.post(reverse("api:entry-refresh", args=[entry.pk])).status_code
        == 502
    )
    monkeypatch.setattr(tvmaze, "request_gate", tvmaze.RequestGate())
    response = viewer_client.post(
        "/api/entries/", {"tvmaze_id": 181}, content_type="application/json"
    )
    assert response.status_code == 400
    assert "tvmaze_id" in response.json()
    assert Entry.objects.count() == 1


def test_deleted_during_refresh_is_json_404_without_resurrection(
    viewer_client, entry_factory
):
    entry = entry_factory()
    pk = entry.pk

    def fetch(_):
        Entry.objects.filter(pk=pk).delete()
        return {"title": "Too late"}

    with patch("shows.operations.get_show", side_effect=fetch):
        response = viewer_client.post(reverse("api:entry-refresh", args=[pk]))
    assert response.status_code == 404
    assert "detail" in response.json()
    assert not Entry.objects.filter(pk=pk).exists()


@pytest.mark.parametrize("staff", [False, True])
def test_new_actions_are_owner_scoped_including_staff(
    viewer_client, viewer, entry_factory, django_user_model, provider_http, staff
):
    viewer.is_staff = staff
    viewer.save()
    foreign = entry_factory(
        owner=django_user_model.objects.create_user(username="other")
    )
    before = Entry.objects.values().get(pk=foreign.pk)
    for pk in [foreign.pk, 99999]:
        for method, path in [
            ("delete", f"/api/entries/{pk}/"),
            ("post", f"/api/entries/{pk}/refresh/"),
        ]:
            response = getattr(viewer_client, method)(path)
            assert response.status_code == 404
            assert "detail" in response.json()
    assert Entry.objects.values().get(pk=foreign.pk) == before
    provider_http[0].assert_not_called()


@pytest.mark.parametrize("method,suffix", [("delete", ""), ("post", "refresh/")])
def test_new_actions_require_authentication(
    client, entry_factory, provider_http, method, suffix
):
    entry = entry_factory()
    response = getattr(client, method)(f"/api/entries/{entry.pk}/{suffix}")
    assert response.status_code == 403
    assert "detail" in response.json()
    assert "Location" not in response
    assert Entry.objects.filter(pk=entry.pk).exists()
    provider_http[0].assert_not_called()


@pytest.mark.parametrize("method,suffix", [("delete", ""), ("post", "refresh/")])
@pytest.mark.parametrize(
    "data",
    [
        {"owner": 1},
        {"title": "forged"},
        {"url": "https://evil.invalid"},
        {"notes": "forged"},
        [],
        "bad",
    ],
)
def test_actions_reject_client_overrides(
    viewer_client, entry_factory, provider_http, method, suffix, data
):
    entry = entry_factory()
    before = Entry.objects.values().get(pk=entry.pk)
    response = getattr(viewer_client, method)(
        f"/api/entries/{entry.pk}/{suffix}", data, content_type="application/json"
    )
    assert response.status_code == 400
    assert Entry.objects.values().get(pk=entry.pk) == before
    provider_http[0].assert_not_called()


@pytest.mark.parametrize("method,suffix", [("delete", ""), ("post", "refresh/")])
def test_actions_reject_query_overrides(
    viewer_client, entry_factory, provider_http, method, suffix
):
    entry = entry_factory()
    response = getattr(viewer_client, method)(
        f"/api/entries/{entry.pk}/{suffix}?url=https://evil.invalid"
    )
    assert response.status_code == 400
    assert Entry.objects.filter(pk=entry.pk).exists()
    provider_http[0].assert_not_called()


@pytest.mark.parametrize(
    "method,suffix",
    [
        ("get", "refresh/"),
        ("put", "refresh/"),
        ("patch", "refresh/"),
        ("delete", "refresh/"),
        ("post", ""),
        ("delete", "list"),
    ],
)
def test_unsupported_methods_preserve_state(
    viewer_client, entry_factory, provider_http, method, suffix
):
    entry = entry_factory()
    before = Entry.objects.values().get(pk=entry.pk)
    path = "/api/entries/" if suffix == "list" else f"/api/entries/{entry.pk}/{suffix}"
    assert getattr(viewer_client, method)(path).status_code == 405
    assert Entry.objects.values().get(pk=entry.pk) == before
    provider_http[0].assert_not_called()


def test_refresh_and_delete_enforce_real_session_csrf(
    viewer, entry_factory, provider_http, show_payload
):
    client = Client(enforce_csrf_checks=True)
    client.get("/accounts/login/")
    token = client.cookies["csrftoken"].value
    response = client.post(
        "/accounts/login/",
        {
            "username": viewer.username,
            "password": "Test-only-947!Moon",
            "csrfmiddlewaretoken": token,
        },
    )
    assert response.status_code == 302
    token = client.cookies["csrftoken"].value
    entry = entry_factory()
    before = Entry.objects.values().get(pk=entry.pk)
    for method, path in [
        ("post", f"/api/entries/{entry.pk}/refresh/"),
        ("delete", f"/api/entries/{entry.pk}/"),
    ]:
        for headers in [{}, {"HTTP_X_CSRFTOKEN": "x" * 32}]:
            response = getattr(client, method)(path, **headers)
            assert response.status_code == 403
            assert "detail" in response.json()
            assert Entry.objects.values().get(pk=entry.pk) == before
    provider_http[0].assert_not_called()
    provider_http[1].json.return_value = show_payload
    assert (
        client.post(
            f"/api/entries/{entry.pk}/refresh/", HTTP_X_CSRFTOKEN=token
        ).status_code
        == 200
    )
    assert (
        client.delete(f"/api/entries/{entry.pk}/", HTTP_X_CSRFTOKEN=token).status_code
        == 204
    )


def test_complete_website_api_workflow(
    viewer_client, provider_http, show_payload, monkeypatch
):
    from . import tvmaze

    now = [100.0]
    monkeypatch.setattr(tvmaze.time, "monotonic", lambda: now[0])
    provider_http[1].json.return_value = show_payload
    response = viewer_client.post(reverse("shows:save", args=[180]))
    assert response.status_code == 302
    entry = Entry.objects.get()
    path = reverse("api:entry-detail", args=[entry.pk])
    personal = dict(
        rating=9,
        notes="<b>Private</b>\nSecond line",
        watch_status="completed",
        last_season=0,
        last_episode=1,
    )
    assert (
        viewer_client.patch(path, personal, content_type="application/json").status_code
        == 200
    )
    page = viewer_client.get(response.url)
    assert b"&lt;b&gt;Private&lt;/b&gt;" in page.content
    assert b"Second line" in page.content
    assert b"CC BY-SA 4.0" in page.content
    now[0] += 2
    provider_http[1].json.return_value = {
        **show_payload,
        "name": "Refreshed cross-surface title",
    }
    refreshed = viewer_client.post(reverse("api:entry-refresh", args=[entry.pk]))
    assert refreshed.status_code == 200
    assert all(refreshed.json()[key] == value for key, value in personal.items())
    assert b"Refreshed cross-surface title" in viewer_client.get(response.url).content
    assert viewer_client.delete(path).status_code == 204
    assert viewer_client.get(response.url).status_code == 404
    assert viewer_client.get(path).status_code == 404
    assert viewer_client.get(reverse("shows:library")).context["has_entries"] is False


def test_local_website_api_workflow_during_provider_outage(
    viewer_client, entry_factory, provider_http
):
    entry = entry_factory()
    second = entry_factory(tvmaze_id=181, title="Second local show")
    get = provider_http[0]
    get.side_effect = AssertionError(
        "Provider access is forbidden for local operations"
    )
    original = viewer_client.get(reverse("api:entry-detail", args=[entry.pk])).json()
    duplicate = viewer_client.post(
        reverse("api:entry-list"), {"tvmaze_id": 180}, content_type="application/json"
    )
    assert duplicate.status_code == 200
    assert duplicate.json() == original
    controls = {"q": "Fire", "status": "planned", "sort": "rating"}
    assert viewer_client.get(reverse("shows:library"), controls).status_code == 200
    assert (
        viewer_client.get(
            reverse("shows:library"), controls, HTTP_HX_REQUEST="true"
        ).status_code
        == 200
    )
    assert viewer_client.get(reverse("api:entry-list"), controls).json()["count"] == 1
    assert (
        viewer_client.get(reverse("shows:detail", args=[entry.pk])).status_code == 200
    )
    assert (
        viewer_client.post(
            reverse("shows:edit", args=[entry.pk]),
            dict(
                rating=8,
                notes="Website outage edit",
                watch_status="paused",
                last_season=0,
                last_episode=1,
            ),
        ).status_code
        == 302
    )
    assert (
        viewer_client.get(reverse("api:entry-detail", args=[entry.pk])).json()["notes"]
        == "Website outage edit"
    )
    assert (
        viewer_client.patch(
            reverse("api:entry-detail", args=[entry.pk]),
            {"notes": "API outage edit"},
            content_type="application/json",
        ).status_code
        == 200
    )
    assert (
        b"API outage edit"
        in viewer_client.get(reverse("shows:detail", args=[entry.pk])).content
    )
    assert (
        viewer_client.get(reverse("shows:delete", args=[second.pk])).status_code == 200
    )
    assert (
        viewer_client.post(reverse("shows:delete", args=[second.pk])).status_code == 302
    )
    assert (
        viewer_client.delete(reverse("api:entry-detail", args=[entry.pk])).status_code
        == 204
    )
    assert not Entry.objects.exists()
    get.assert_not_called()

import pytest
from django.test import Client
from django.urls import reverse

from .models import Entry

pytestmark = pytest.mark.django_db


def test_confirmation_cancel_and_delete_are_local(
    viewer_client, entry_factory, provider_http
):
    entry = entry_factory(
        notes="Gone", rating=10, watch_status="completed", last_season=1, last_episode=2
    )
    provider_http[0].side_effect = AssertionError("Deletion must be local")
    url = reverse("shows:delete", args=[entry.pk])
    before = Entry.objects.values().get(pk=entry.pk)
    confirmation = viewer_client.get(url)
    assert confirmation.status_code == 200
    for text in (
        b"Firefly",
        b"notes",
        b"rating",
        b"watch status",
        b"bookmark",
        b"permanently",
        b"Cancel",
    ):
        assert text in confirmation.content
    viewer_client.get(reverse("shows:detail", args=[entry.pk]))
    assert Entry.objects.values().get(pk=entry.pk) == before
    response = viewer_client.post(url)
    assert response.status_code == 302
    assert response.url == reverse("shows:library")
    assert not Entry.objects.filter(pk=entry.pk).exists()
    provider_http[0].assert_not_called()


def test_resave_after_deletion_starts_fresh(
    viewer_client, entry_factory, provider_http, show_payload
):
    entry = entry_factory(
        notes="Gone", rating=10, watch_status="completed", last_season=1, last_episode=2
    )
    viewer_client.post(reverse("shows:delete", args=[entry.pk]))
    provider_http[1].json.return_value = show_payload
    assert viewer_client.post(reverse("shows:save", args=[180])).status_code == 302
    fresh = Entry.objects.get()
    assert fresh.pk != entry.pk
    assert fresh.notes == ""
    assert fresh.rating is None
    assert fresh.watch_status == "planned"
    assert fresh.last_season is fresh.last_episode is None


@pytest.mark.parametrize(
    "action,method", [("refresh", "post"), ("delete", "get"), ("delete", "post")]
)
@pytest.mark.parametrize("staff", [False, True])
def test_actions_are_owner_scoped(
    viewer_client,
    entry_factory,
    django_user_model,
    provider_http,
    action,
    method,
    staff,
):
    user = viewer_client.session["_auth_user_id"]
    django_user_model.objects.filter(pk=user).update(is_staff=staff, is_superuser=staff)
    other = django_user_model.objects.create_user(username="other")
    entry = entry_factory(owner=other)
    before = Entry.objects.values().get(pk=entry.pk)
    response = getattr(viewer_client, method)(
        reverse(f"shows:{action}", args=[entry.pk])
    )
    missing = getattr(viewer_client, method)(reverse(f"shows:{action}", args=[99999]))
    assert response.status_code == missing.status_code == 404
    assert Entry.objects.values().get(pk=entry.pk) == before
    provider_http[0].assert_not_called()


@pytest.mark.parametrize("action", ["refresh", "delete"])
def test_actions_require_login_and_csrf(
    client, viewer, entry_factory, provider_http, action
):
    entry = entry_factory()
    url = reverse(f"shows:{action}", args=[entry.pk])
    assert client.post(url).status_code == 302
    secured = Client(enforce_csrf_checks=True)
    secured.force_login(viewer)
    assert secured.post(url).status_code == 403
    page = secured.get(reverse("shows:detail", args=[entry.pk]))
    assert page.status_code == 200
    if action == "refresh":
        provider_http[1].json.return_value = {
            "id": 180,
            "name": "Fresh",
            "url": entry.source_url,
        }
    response = secured.post(
        url, {"csrfmiddlewaretoken": secured.cookies["csrftoken"].value}
    )
    assert response.status_code == 302


@pytest.mark.parametrize(
    "action,method",
    [("refresh", "get"), ("refresh", "put"), ("delete", "put"), ("delete", "delete")],
)
def test_unsupported_methods_do_not_mutate(
    viewer_client, entry_factory, provider_http, action, method
):
    entry = entry_factory()
    before = Entry.objects.values().get(pk=entry.pk)
    response = getattr(viewer_client, method)(
        reverse(f"shows:{action}", args=[entry.pk])
    )
    assert response.status_code == 405
    assert Entry.objects.values().get(pk=entry.pk) == before
    provider_http[0].assert_not_called()


@pytest.mark.parametrize("action", ["refresh", "delete"])
@pytest.mark.parametrize("mode", ["extra", "query", "json", "file"])
def test_actions_reject_forged_payloads(
    viewer_client, entry_factory, provider_http, action, mode
):
    from django.core.files.uploadedfile import SimpleUploadedFile

    entry = entry_factory()
    url = reverse(f"shows:{action}", args=[entry.pk])
    before = Entry.objects.values().get(pk=entry.pk)
    if mode == "query":
        response = viewer_client.post(url + "?owner=99")
    elif mode == "json":
        response = viewer_client.post(url, {}, content_type="application/json")
    elif mode == "file":
        response = viewer_client.post(
            url, {"file": SimpleUploadedFile("x.txt", b"bad")}
        )
    else:
        response = viewer_client.post(url, {"title": "Forged", "owner": 99})
    assert response.status_code == 400
    assert Entry.objects.values().get(pk=entry.pk) == before
    provider_http[0].assert_not_called()

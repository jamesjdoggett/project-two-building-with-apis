from unittest.mock import patch

import pytest
import requests
from django.test import Client

from .models import Entry
from .operations import SaveBusy
from .personal import PERSONAL_FIELDS, WATCH_STATUSES
from .tvmaze import ProviderError, RateLimited, ShowNotFound

pytestmark = pytest.mark.django_db


def test_list_is_private_local_and_has_provenance(
    viewer_client, entry_factory, django_user_model, provider_http
):
    owned = entry_factory()
    other = django_user_model.objects.create_user(username="other")
    entry_factory(owner=other, tvmaze_id=181)
    response = viewer_client.get("/api/entries/")
    assert response.status_code == 200
    data = response.json()
    assert [row["id"] for row in data["results"]] == [owned.pk]
    assert data["results"][0]["provider_name"] == "TVmaze"
    assert "owner" not in data["results"][0]
    provider_http[0].assert_not_called()


def url(entry):
    return f"/api/entries/{entry.pk}/"


def write(client, path, data, method="patch"):
    return getattr(client, method)(path, data, content_type="application/json")


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/entries/"),
        ("post", "/api/entries/"),
        ("get", "/api/entries/1/"),
        ("put", "/api/entries/1/"),
        ("patch", "/api/entries/1/"),
    ],
)
def test_anonymous_json_error(client, method, path):
    response = getattr(client, method)(path, content_type="application/json")
    assert response.status_code == 403
    assert "detail" in response.json()
    assert "Location" not in response


@pytest.mark.parametrize("staff", [False, True])
def test_owner_scoping(viewer_client, viewer, entry_factory, django_user_model, staff):
    viewer.is_staff = viewer.is_superuser = staff
    viewer.save()
    other = django_user_model.objects.create_user(username="other")
    foreign = entry_factory(owner=other)
    for path in [url(foreign), "/api/entries/99999/"]:
        assert viewer_client.get(path).status_code == 404
        for method in ["put", "patch"]:
            assert (
                write(viewer_client, path, {"notes": "stolen"}, method).status_code
                == 404
            )
    assert viewer_client.get("/api/entries/").json()["count"] == 0
    foreign.refresh_from_db()
    assert foreign.notes == ""


def test_query_and_pagination_parity(viewer_client, entry_factory, provider_http):
    from .library import library_entries

    for i in range(23):
        entry_factory(
            tvmaze_id=i + 1, title=f"Series {i:02}", rating=None if i % 2 else 8
        )
    for params in [
        dict(q="  SERIES  ", status="bad", sort="bad"),
        dict(sort="title"),
        dict(sort="rating"),
        dict(status="planned", q="Series"),
    ]:
        expected, controls = library_entries(
            viewer_client.session.get("_auth_user_id"), params
        )
        response = viewer_client.get("/api/entries/", params).json()
        assert response["count"] == 23
        assert len(response["results"]) == 20
        assert [row["id"] for row in response["results"]] == list(
            expected.values_list("pk", flat=True)[:20]
        )
        assert all(response[key] == value for key, value in controls.items())
        assert response["next"] == 2
    for page, expected in [("bad", 1), ("999", 2), ("-1", 2)]:
        assert (
            viewer_client.get("/api/entries/", {"page": page}).json()["page"]
            == expected
        )
    provider_http[0].assert_not_called()


def test_create_duplicate_and_website(viewer_client, provider_http, show_payload):
    get, upstream = provider_http
    upstream.json.return_value = show_payload
    response = write(viewer_client, "/api/entries/", {"tvmaze_id": 180}, "post")
    assert response.status_code == 201
    row = response.json()
    assert (
        row["rating"],
        row["notes"],
        row["watch_status"],
        row["last_season"],
        row["last_episode"],
    ) == (None, "", "planned", None, None)
    assert row["summary"] == "A space adventure & friends."
    assert row["license_url"] == "https://creativecommons.org/licenses/by-sa/4.0/"
    assert row["summary_transformation"]
    get.reset_mock()
    get.side_effect = AssertionError("No HTTP for duplicate or local reads")
    duplicate = write(viewer_client, "/api/entries/", {"tvmaze_id": 180}, "post")
    assert duplicate.status_code == 200
    assert duplicate.json() == row
    assert viewer_client.get(f"/library/{row['id']}/").status_code == 200
    assert viewer_client.get(f"/api/entries/{row['id']}/").json() == row
    get.assert_not_called()


@pytest.mark.parametrize("value", [True, False, 0, -1, 1.5, 180.0, "180", None, 2**63])
def test_bad_create_ids(viewer_client, provider_http, value):
    assert (
        write(viewer_client, "/api/entries/", {"tvmaze_id": value}, "post").status_code
        == 400
    )
    assert not Entry.objects.exists()
    provider_http[0].assert_not_called()


@pytest.mark.parametrize(
    "field",
    [
        "owner",
        "owner_id",
        "title",
        "source_url",
        "url",
        "rating",
        "notes",
        "watch_status",
        "last_season",
        "poster_url",
    ],
)
def test_create_overrides_rejected(viewer_client, provider_http, field):
    response = write(
        viewer_client, "/api/entries/", {"tvmaze_id": 180, field: "forged"}, "post"
    )
    assert response.status_code == 400
    assert field in response.json()
    provider_http[0].assert_not_called()


@pytest.mark.parametrize(
    "failure,status",
    [
        (requests.Timeout(), 504),
        (RateLimited(7), 503),
        (ShowNotFound("secret"), 400),
        (ProviderError("<html>secret</html>"), 502),
        (SaveBusy(), 503),
    ],
)
def test_create_error_mapping(viewer_client, failure, status):
    with patch("shows.api.save_entry", side_effect=failure):
        response = write(viewer_client, "/api/entries/", {"tvmaze_id": 180}, "post")
    assert response.status_code == status
    assert "secret" not in str(response.json())
    if status == 503:
        assert int(response["Retry-After"]) >= 1
        assert response.json()["retry_after"] >= 1
    assert not Entry.objects.exists()


@pytest.mark.parametrize(
    "scenario,status",
    [
        ("timeout", 504),
        ("connection", 502),
        ("404", 400),
        ("429", 503),
        ("500", 502),
        ("malformed", 502),
        ("mismatch", 502),
    ],
)
def test_real_provider_failures(
    viewer_client, provider_http, show_payload, scenario, status
):
    get, upstream = provider_http
    upstream.json.return_value = show_payload
    if scenario == "timeout":
        get.side_effect = requests.Timeout
    elif scenario == "connection":
        get.side_effect = requests.ConnectionError
    elif scenario.isdigit():
        upstream.status_code = int(scenario)
    elif scenario == "malformed":
        upstream.json.return_value = []
    else:
        upstream.json.return_value = {**show_payload, "id": 181}
    response = write(viewer_client, "/api/entries/", {"tvmaze_id": 180}, "post")
    assert response.status_code == status
    assert not Entry.objects.exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("rating", 0),
        ("rating", 11),
        ("rating", True),
        ("rating", 2.5),
        ("rating", "2"),
        ("rating", 2.0),
        ("notes", "x" * 5001),
        ("notes", None),
        ("notes", 42),
        ("watch_status", "unknown"),
        ("watch_status", True),
        ("last_season", -1),
        ("last_season", 1.1),
        ("last_season", True),
        ("last_season", "1"),
        ("last_episode", 0),
        ("last_episode", 1.5),
        ("last_episode", False),
        ("last_episode", 2**63),
    ],
)
def test_invalid_personal_state_preserved(viewer_client, entry_factory, field, value):
    entry = entry_factory(last_season=1, last_episode=2)
    before = Entry.objects.values().get(pk=entry.pk)
    response = write(viewer_client, url(entry), {field: value})
    assert response.status_code == 400
    assert Entry.objects.values().get(pk=entry.pk) == before


@pytest.mark.parametrize("status,_label", WATCH_STATUSES)
def test_independence_put_patch_and_site(
    viewer_client, entry_factory, provider_http, status, _label
):
    entry = entry_factory(watch_status=status, last_season=3, last_episode=4)
    get = provider_http[0]
    get.side_effect = AssertionError("Local editing must not call TVmaze")
    assert (
        write(viewer_client, url(entry), {"last_season": 0, "last_episode": 1}).json()[
            "watch_status"
        ]
        == status
    )
    response = write(viewer_client, url(entry), {"watch_status": "completed"})
    assert response.json()["last_season"] == 0
    assert response.json()["last_episode"] == 1
    assert write(viewer_client, url(entry), {"last_season": None}).status_code == 400
    assert (
        write(
            viewer_client, url(entry), {"last_season": None, "last_episode": None}
        ).status_code
        == 200
    )
    state = dict(
        rating=10,
        notes="<b>private</b>\nline two",
        watch_status=status,
        last_season=0,
        last_episode=1,
    )
    assert write(viewer_client, url(entry), state, "put").status_code == 200
    assert write(viewer_client, url(entry), {"rating": 1}, "put").status_code == 400
    page = viewer_client.get(f"/library/{entry.pk}/").content.decode()
    assert "&lt;b&gt;private&lt;/b&gt;" in page
    assert "line two" in page
    for rating in [None, 1, 10]:
        assert (
            write(
                viewer_client, url(entry), {"rating": rating, "notes": "x" * 5000}
            ).status_code
            == 200
        )
    get.assert_not_called()


@pytest.mark.parametrize(
    "field",
    [
        "owner",
        "owner_id",
        "tvmaze_id",
        "title",
        "summary",
        "source_url",
        "retrieved_at",
        "id",
        "provider_name",
        "license_url",
        "clear_bookmark",
    ],
)
@pytest.mark.parametrize("method", ["put", "patch"])
def test_update_server_fields_rejected(viewer_client, entry_factory, field, method):
    entry = entry_factory()
    state = {name: getattr(entry, name) for name in PERSONAL_FIELDS}
    response = write(viewer_client, url(entry), {**state, field: "forged"}, method)
    assert response.status_code == 400
    entry.refresh_from_db()
    assert entry.notes == ""


def test_real_session_csrf(viewer, entry_factory, provider_http):
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
    for method, path, payload in [
        ("post", "/api/entries/", {"tvmaze_id": 180}),
        ("put", url(entry), {name: getattr(entry, name) for name in PERSONAL_FIELDS}),
        ("patch", url(entry), {"notes": "new"}),
    ]:
        assert write(client, path, payload, method).status_code == 403
        response = getattr(client, method)(
            path, payload, content_type="application/json", HTTP_X_CSRFTOKEN=token
        )
        assert response.status_code == 200
    provider_http[0].assert_not_called()


def test_phase_six_actions_unavailable(viewer_client, entry_factory):
    entry = entry_factory()
    assert viewer_client.delete(url(entry)).status_code == 405
    assert viewer_client.post(url(entry) + "refresh/").status_code == 404
    assert Entry.objects.filter(pk=entry.pk).exists()


@pytest.mark.parametrize("missing", PERSONAL_FIELDS)
def test_put_requires_each_personal_field(viewer_client, entry_factory, missing):
    entry = entry_factory()
    state = {name: getattr(entry, name) for name in PERSONAL_FIELDS if name != missing}
    response = write(viewer_client, url(entry), state, "put")
    assert response.status_code == 400
    assert missing in response.json()


def test_patch_pair_merge_and_absent_pair(viewer_client, entry_factory):
    entry = entry_factory()
    assert write(viewer_client, url(entry), {"last_season": 0}).status_code == 400
    assert (
        write(
            viewer_client, url(entry), {"last_season": 0, "last_episode": 1}
        ).status_code
        == 200
    )
    assert write(viewer_client, url(entry), {"last_episode": 8}).status_code == 200
    entry.refresh_from_db()
    assert (entry.last_season, entry.last_episode, entry.watch_status) == (
        0,
        8,
        "planned",
    )


def test_create_collision_returns_committed_winner(
    viewer_client, viewer, entry_factory, provider_http, show_payload
):
    # Simulate another request committing after the initial duplicate lookup but
    # before this request reaches the shared operation's atomic get_or_create.
    get, upstream = provider_http
    upstream.json.return_value = show_payload

    def competing_save(*args, **kwargs):
        entry_factory(title="Winner", notes="Preserve this")
        return get.return_value

    get.side_effect = competing_save
    response = write(viewer_client, "/api/entries/", {"tvmaze_id": 180}, "post")
    assert response.status_code == 200
    assert response.json()["notes"] == "Preserve this"
    assert response.json()["title"] == "Winner"
    assert Entry.objects.filter(owner=viewer, tvmaze_id=180).count() == 1


@pytest.mark.parametrize("data", [[], "bad", None])
def test_non_object_writes_rejected(viewer_client, entry_factory, data):
    entry = entry_factory()
    assert write(viewer_client, url(entry), data).status_code == 400
    assert write(viewer_client, "/api/entries/", data, "post").status_code == 400


def test_browsable_api_and_empty_list(viewer_client, entry_factory):
    data = viewer_client.get("/api/entries/").json()
    assert data == dict(
        count=0,
        page=1,
        pages=1,
        next=None,
        previous=None,
        q="",
        status="",
        sort="recent",
        results=[],
    )
    entry = entry_factory()
    for path in ["/api/entries/", url(entry)]:
        response = viewer_client.get(path, HTTP_ACCEPT="text/html")
        assert response.status_code == 200
        assert b"text/html" in response["Content-Type"].encode()
        assert b'"csrfToken":' in response.content
        assert "csrftoken" in viewer_client.cookies
        assert b'name="_content"' in response.content


def test_api_save_same_show_is_independent(
    viewer_client, entry_factory, django_user_model, provider_http, show_payload
):
    other = django_user_model.objects.create_user(username="other")
    foreign = entry_factory(
        owner=other, title="Other snapshot", notes="Other private notes"
    )
    provider_http[1].json.return_value = show_payload
    response = write(viewer_client, "/api/entries/", {"tvmaze_id": 180}, "post")
    assert response.status_code == 201
    assert response.json()["id"] != foreign.pk
    assert response.json()["notes"] == ""
    assert "Other private notes" not in str(response.json())
    foreign.refresh_from_db()
    assert foreign.title == "Other snapshot"
    assert foreign.notes == "Other private notes"

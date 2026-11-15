import re

import pytest
from django.urls import reverse

from . import tvmaze
from .models import Entry

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("name", ["discover", "library"])
def test_expired_fragment_session_navigates_to_login(client, name):
    response = client.get(
        reverse(f"shows:{name}"), {"q": "Firefly"}, HTTP_HX_REQUEST="true"
    )
    assert response.status_code == 200
    assert response["HX-Redirect"].startswith(reverse("login") + "?next=")
    assert "Firefly" in response["HX-Redirect"]
    assert not response.content


@pytest.mark.parametrize("name", ["discover", "library"])
def test_full_and_fragment_responses_share_results_and_controls(
    viewer_client, entry_factory, provider_http, name, monkeypatch
):
    entry_factory()
    params = {"q": "  Firefly  ", "status": "bad", "sort": "bad"}
    full = viewer_client.get(reverse(f"shows:{name}"), params)
    monkeypatch.setattr(tvmaze, "request_gate", tvmaze.RequestGate())
    partial = viewer_client.get(
        reverse(f"shows:{name}"), params, HTTP_HX_REQUEST="true"
    )
    assert full.status_code == partial.status_code == 200

    # Django masks the same CSRF secret differently on each render.
    def without_csrf(content):
        return re.sub(rb'name="csrfmiddlewaretoken" value="[^"]+"', b"csrf", content)

    assert without_csrf(partial.content).strip() in without_csrf(full.content)
    assert b"<!doctype" not in partial.content
    assert b"Main navigation" not in partial.content
    assert b'value="Firefly"' in partial.content
    assert f'id="{name}-panel"'.encode() in partial.content
    assert b"htmx-indicator" in partial.content
    assert b"HX-Request" in partial["Vary"].encode()
    assert b"hx-get=" in full.content
    assert b"shows/htmx.min.js" in full.content
    if name == "library":
        assert b'value="recent" selected' in partial.content
        provider_http[0].assert_not_called()
    else:
        assert b"Saved</span>" in partial.content


@pytest.mark.parametrize(
    "failure,message",
    [
        ("timeout", "timed out"),
        ("connection", "Could not connect"),
        ("json", "invalid data"),
        ("shape", "invalid data"),
        ("429", "Wait 12 seconds"),
        ("404", "unavailable"),
        ("500", "unavailable"),
    ],
)
def test_fragment_discovery_failures_retain_form_query(
    viewer_client, provider_http, failure, message
):
    import requests

    get, upstream = provider_http
    if failure == "timeout":
        get.side_effect = requests.Timeout()
    elif failure == "connection":
        get.side_effect = requests.ConnectionError()
    elif failure == "json":
        upstream.json.side_effect = requests.exceptions.JSONDecodeError("bad", "x", 0)
    elif failure == "shape":
        upstream.json.return_value = {}
    else:
        upstream.status_code = int(failure)
        upstream.headers = {"Retry-After": "12"}
    response = viewer_client.get(
        reverse("shows:discover"), {"q": "  Firefly  "}, HTTP_HX_REQUEST="true"
    )
    assert response.status_code == 200
    assert message.encode() in response.content
    assert b'value="Firefly"' in response.content
    assert b'role="alert"' in response.content
    assert b"No shows found" not in response.content
    assert b"<!doctype" not in response.content


def test_local_fragment_pagination_and_empty_states(
    viewer_client, entry_factory, provider_http
):
    provider_http[0].side_effect = AssertionError("Local fragments cannot call TVmaze")
    url = reverse("shows:library")
    empty = viewer_client.get(url, HTTP_HX_REQUEST="true")
    assert b"Your library is empty" in empty.content
    for i in range(21):
        entry_factory(tvmaze_id=i + 1, title="Space show", watch_status="paused")
    params = {"q": " Space ", "status": "paused", "sort": "title", "page": "2"}
    response = viewer_client.get(url, params, HTTP_HX_REQUEST="true")
    assert len(response.context["page_obj"]) == 1
    assert b"Page 2 of 2" in response.content
    assert b"q=Space&amp;status=paused&amp;sort=title&amp;page=1" in response.content
    assert b"hx-boost=" in response.content
    params["q"] = "No match"
    no_match = viewer_client.get(url, params, HTTP_HX_REQUEST="true")
    assert b"No saved shows match" in no_match.content
    provider_http[0].assert_not_called()


def test_saved_indicator_tracks_save_and_delete(
    viewer_client, provider_http, show_payload, monkeypatch
):
    def discover():
        monkeypatch.setattr(tvmaze, "request_gate", tvmaze.RequestGate())
        provider_http[1].json.return_value = [{"show": show_payload}]
        return viewer_client.get(
            reverse("shows:discover"), {"q": "Firefly"}, HTTP_HX_REQUEST="true"
        )

    assert b"Saved</span>" not in discover().content
    monkeypatch.setattr(tvmaze, "request_gate", tvmaze.RequestGate())
    provider_http[1].json.return_value = show_payload
    viewer_client.post(reverse("shows:save", args=[180]))
    assert b"Saved</span>" in discover().content
    viewer_client.post(reverse("shows:delete", args=[Entry.objects.get().pk]))
    assert b"Saved</span>" not in discover().content


def test_empty_fragment_search_is_normal_and_blank_query_does_not_fetch(
    viewer_client, provider_http
):
    blank = viewer_client.get(
        reverse("shows:discover"), {"q": " "}, HTTP_HX_REQUEST="true"
    )
    assert b"Enter a show title" in blank.content
    provider_http[0].assert_not_called()
    provider_http[1].json.return_value = []
    empty = viewer_client.get(
        reverse("shows:discover"), {"q": "Nobody"}, HTTP_HX_REQUEST="true"
    )
    assert b"No shows found" in empty.content
    assert b'role="alert"' not in empty.content


def test_fragment_requests_are_get_only(viewer_client, provider_http):
    for name in ("library", "discover"):
        assert (
            viewer_client.post(
                reverse(f"shows:{name}"), HTTP_HX_REQUEST="true"
            ).status_code
            == 405
        )
    provider_http[0].assert_not_called()

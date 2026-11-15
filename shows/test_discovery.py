from unittest.mock import patch

import pytest
import requests
from django.test import Client
from django.urls import reverse

from . import tvmaze


@pytest.mark.django_db
def test_blank_search_is_rejected_before_provider_call(client, django_user_model):
    user = django_user_model.objects.create_user(username="viewer")
    client.force_login(user)

    with patch("shows.views.search_shows", return_value=[]) as search:
        response = client.get(reverse("shows:discover"), {"q": "   "})

    assert response.status_code == 200
    search.assert_not_called()
    assert b"Enter a show title" in response.content


@pytest.mark.django_db
def test_timeout_shows_retry_guidance_and_retains_query(client, django_user_model):
    user = django_user_model.objects.create_user(username="viewer")
    client.force_login(user)
    client.raise_request_exception = False

    with patch("shows.views.search_shows", side_effect=requests.Timeout) as search:
        response = client.get(reverse("shows:discover"), {"q": "Firefly"})

    assert response.status_code == 200
    assert b"timed out" in response.content
    assert b"Try again" in response.content
    assert b'value="Firefly"' in response.content
    search.assert_called_once_with("Firefly")


@pytest.mark.django_db
def test_discovery_renders_provider_order_all_results_and_attribution(
    viewer_client, provider_http, show_payload
):
    get, response = provider_http
    response.json.return_value = [
        {"show": {**show_payload, "id": i + 1, "name": f"Result {i}"}} for i in range(7)
    ]
    page = viewer_client.get(reverse("shows:discover"), {"q": "  A & B?  "})
    assert page.status_code == 200
    html = page.content.decode()
    assert [show.title for show in page.context["results"]] == [
        f"Result {i}" for i in range(7)
    ]
    assert html.index("Result 0") < html.index("Result 6")
    assert "7 matches" in html
    assert "Premiered 2002" in html
    assert "A space adventure &amp; friends." in html
    assert "<b>space</b>" not in html
    assert 'href="https://www.tvmaze.com/shows/180/firefly"' in html
    assert "https://creativecommons.org/licenses/by-sa/4.0/" in html
    assert "Summaries converted from HTML to plain text" in html
    assert get.call_args.kwargs["params"] == {"q": "A & B?"}
    assert b'name="q" value="A &amp; B?"' in page.content


@pytest.mark.django_db
def test_missing_optional_data_has_local_fallbacks(viewer_client, provider_http):
    provider_http[1].json.return_value = [
        {"show": {"id": 1, "name": "Mystery", "url": "https://www.tvmaze.com/shows/1"}}
    ]
    page = viewer_client.get(reverse("shows:discover"), {"q": "Mystery"})
    assert page.status_code == 200
    assert b"Premiere year unknown" in page.content
    assert b"No summary available." in page.content
    assert b'src="/static/shows/poster-placeholder.svg"' in page.content
    assert b'data-fallback="/static/shows/poster-placeholder.svg"' in page.content


@pytest.mark.django_db
def test_provider_text_and_query_are_escaped(
    viewer_client, provider_http, show_payload
):
    provider_http[1].json.return_value = [
        {
            "show": {
                **show_payload,
                "name": '<img src=x onerror="alert(1)">',
                "summary": "<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>",
            }
        }
    ]
    page = viewer_client.get(
        reverse("shows:discover"), {"q": '"><script>alert(2)</script>'}
    )
    assert page.status_code == 200
    assert b"<script>alert" not in page.content
    assert b'<img src=x onerror="alert' not in page.content
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in page.content


@pytest.mark.django_db
def test_initial_discovery_and_blank_queries_do_not_use_http(
    viewer_client, provider_http
):
    for params in ({}, {"q": ""}, {"q": "   "}):
        page = viewer_client.get(reverse("shows:discover"), params)
        assert page.status_code == 200
        assert b"Enter a show title" in page.content
    provider_http[0].assert_not_called()


@pytest.mark.django_db
def test_empty_results_are_normal_and_retain_query(viewer_client, provider_http):
    provider_http[1].json.return_value = []
    page = viewer_client.get(reverse("shows:discover"), {"q": "Unknown title"})
    assert page.status_code == 200
    assert b"No shows found" in page.content
    assert b'value="Unknown title"' in page.content
    assert b'role="alert"' not in page.content


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("failure", "message"),
    [
        ("timeout", "timed out"),
        ("connection", "Could not connect"),
        ("json", "invalid data"),
        ("shape", "invalid data"),
        ("429", "Wait 12 seconds"),
        ("404", "unavailable"),
        ("500", "unavailable"),
        ("503", "unavailable"),
    ],
)
def test_http_failures_are_useful_and_retain_query(
    viewer_client, provider_http, failure, message
):
    get, response = provider_http
    if failure == "timeout":
        get.side_effect = requests.Timeout()
    elif failure == "connection":
        get.side_effect = requests.ConnectionError()
    elif failure == "json":
        response.json.side_effect = requests.exceptions.JSONDecodeError("bad", "x", 0)
    elif failure == "shape":
        response.json.return_value = {"error": "not a list"}
    else:
        response.status_code = int(failure)
        response.headers = {"Retry-After": "12"}
    page = viewer_client.get(reverse("shows:discover"), {"q": "Firefly"})
    assert page.status_code == 200
    assert message.encode() in page.content
    assert b'value="Firefly"' in page.content
    assert b'role="alert"' in page.content
    assert b"No shows found" not in page.content
    assert b"Traceback" not in page.content
    get.assert_called_once()


@pytest.mark.django_db
def test_request_gate_is_shared_between_signed_in_users(
    django_user_model, viewer_client, provider_http, monkeypatch
):
    monkeypatch.setattr(tvmaze.time, "monotonic", lambda: 100.0)
    other = django_user_model.objects.create_user(username="other-viewer")
    other_client = Client()
    other_client.force_login(other)
    first = viewer_client.get(reverse("shows:discover"), {"q": "Firefly"})
    second = other_client.get(reverse("shows:discover"), {"q": "Girls"})
    assert first.status_code == second.status_code == 200
    assert b"Wait 1 second" in second.content
    assert b'value="Girls"' in second.content
    provider_http[0].assert_called_once()

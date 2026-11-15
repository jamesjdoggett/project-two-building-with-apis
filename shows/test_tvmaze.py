from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
import requests

from . import tvmaze


def test_request_uses_official_endpoint_encoded_params_identity_and_timeout(
    provider_http,
):
    get, response = provider_http
    shows = tvmaze.search_shows("  A & B?  ")
    assert shows[0].title == "Firefly"
    get.assert_called_once_with(
        tvmaze.SEARCH_URL,
        params={"q": "A & B?"},
        headers={"User-Agent": tvmaze.USER_AGENT},
        timeout=(10, 10),
        allow_redirects=False,
    )
    prepared = requests.Request(
        "GET", tvmaze.SEARCH_URL, params={"q": "A & B?"}
    ).prepare()
    assert prepared.url.endswith("?q=A+%26+B%3F")
    response.__exit__.assert_called_once()


def test_client_also_skips_blank_input(provider_http):
    assert tvmaze.search_shows("  ") == []
    provider_http[0].assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [{}, [None], [1], [[]], [{}], [{"show": None}], [{"show": {}}]],
)
def test_malformed_search_shapes_fail_safely(provider_http, payload):
    provider_http[1].json.return_value = payload
    with pytest.raises(tvmaze.ProviderError, match="invalid data"):
        tvmaze.search_shows("Firefly")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", True),
        ("id", 0),
        ("id", -1),
        ("id", 1.5),
        ("id", "1"),
        ("name", " "),
        ("name", None),
        ("name", 12),
        ("url", "javascript:alert(1)"),
        ("url", "https://evil.example/show"),
        ("premiered", "not-a-date"),
        ("premiered", 123),
        ("summary", []),
        ("image", []),
        ("image", {"medium": "javascript:alert(1)"}),
    ],
)
def test_invalid_display_fields_reject_entire_response(
    provider_http, show_payload, field, value
):
    provider_http[1].json.return_value = [
        {"show": show_payload},
        {"show": {**show_payload, field: value}},
    ]
    with pytest.raises(tvmaze.ProviderError, match="invalid data"):
        tvmaze.search_shows("Firefly")


def test_null_optional_fields_and_original_image_fallback(provider_http, show_payload):
    show = {**show_payload, "premiered": None, "summary": None, "image": None}
    provider_http[1].json.return_value = [{"show": show}]
    result = tvmaze.search_shows("Firefly")[0]
    assert result.premiere_year is None
    assert result.summary == "No summary available."
    assert result.poster_url == ""
    show["image"] = {"medium": None, "original": "https://static.tvmaze.com/poster.jpg"}
    assert tvmaze.parse_show(show).poster_url == "https://static.tvmaze.com/poster.jpg"


@pytest.mark.parametrize("status", [301, 302, 404, 500, 503])
def test_http_errors_are_not_decoded_or_retried(provider_http, status):
    get, response = provider_http
    response.status_code = status
    with pytest.raises(tvmaze.ProviderError):
        tvmaze.search_shows("Firefly")
    get.assert_called_once()
    response.json.assert_not_called()


def test_shared_gate_blocks_second_search_without_http_and_then_allows_it(
    provider_http, monkeypatch
):
    clock = MagicMock(return_value=100.0)
    monkeypatch.setattr(tvmaze.time, "monotonic", clock)
    tvmaze.search_shows("Firefly")
    with pytest.raises(tvmaze.RateLimited) as caught:
        tvmaze.search_shows("Girls")
    assert caught.value.retry_after == 1
    assert provider_http[0].call_count == 1
    clock.return_value = 101.0
    tvmaze.search_shows("Girls")
    assert provider_http[0].call_count == 2


def test_gate_reservation_is_shared_across_threads(monkeypatch):
    monkeypatch.setattr(tvmaze.time, "monotonic", lambda: 100.0)

    def try_request(_):
        try:
            tvmaze.request_gate.acquire()
            return True
        except tvmaze.RateLimited:
            return False

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(try_request, range(8))).count(True) == 1


def test_429_extends_shared_cooldown_and_never_retries(provider_http, monkeypatch):
    clock = MagicMock(return_value=100.0)
    monkeypatch.setattr(tvmaze.time, "monotonic", clock)
    get, response = provider_http
    response.status_code = 429
    response.headers = {"Retry-After": "12"}
    with pytest.raises(tvmaze.RateLimited) as caught:
        tvmaze.search_shows("Firefly")
    assert caught.value.retry_after == 12
    clock.return_value = 105.0
    with pytest.raises(tvmaze.RateLimited) as caught:
        tvmaze.search_shows("Girls")
    assert caught.value.retry_after == 7
    get.assert_called_once()
    clock.return_value = 112.0
    response.status_code = 200
    tvmaze.search_shows("Girls")
    assert get.call_count == 2


@pytest.mark.parametrize("value", [None, "nonsense", "", "inf"])
def test_missing_or_invalid_retry_after_uses_safe_default(value):
    assert tvmaze.retry_after_seconds(value) == 10


def test_retry_after_supports_http_dates(monkeypatch):
    frozen = MagicMock(wraps=datetime)
    frozen.now.return_value = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(tvmaze, "datetime", frozen)
    assert tvmaze.retry_after_seconds("Sat, 14 Nov 2026 12:00:20 GMT") == 20

from io import StringIO
from unittest.mock import patch

import pytest
import requests
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from . import tvmaze
from .tvmaze import ProviderError, get_show, search_shows


@pytest.mark.parametrize(
    ("scenario", "message"),
    [
        ("rate-limit", "Wait 5 seconds"),
        ("malformed", "invalid data"),
        ("timeout", ""),
        ("no-results", ""),
        ("missing-data", ""),
        ("removed", "unavailable"),
    ],
)
@override_settings(DEBUG=True)
def test_demo_intercepts_provider_only_while_loopback_server_runs(scenario, message):
    def verify_server(*args, **kwargs):
        assert args == ("runserver", "127.0.0.1:8000")
        assert kwargs == {"use_reloader": False}
        if scenario == "timeout":
            with pytest.raises(requests.Timeout):
                search_shows("Firefly")
        elif scenario == "no-results":
            assert search_shows("Firefly") == []
        elif scenario == "missing-data":
            shows = search_shows("Firefly")
            assert len(shows) == 2
            assert shows[0].poster_url == ""
            assert shows[0].summary == "No summary available."
            assert shows[1].summary == "Plain text & an unavailable poster."
        else:
            with pytest.raises(ProviderError, match=message):
                search_shows("Firefly")

    with patch(
        "shows.management.commands.discovery_demo.call_command",
        side_effect=verify_server,
    ):
        call_command("discovery_demo", scenario, stdout=StringIO())


@override_settings(DEBUG=False)
def test_demo_is_not_available_with_debug_disabled():
    with pytest.raises(CommandError, match="DEBUG=True"):
        call_command("discovery_demo", "timeout", stdout=StringIO())


@pytest.mark.parametrize("scenario", ["library", "invalid-detail", "refreshed"])
@override_settings(DEBUG=True)
def test_save_demo_has_search_cards_and_controlled_detail_responses(
    scenario, monkeypatch
):
    def verify_server(*args, **kwargs):
        shows = search_shows("demo")
        assert len(shows) == 21
        assert shows[0].title == "Demo show 01"
        monkeypatch.setattr(tvmaze, "request_gate", tvmaze.RequestGate())
        if scenario == "invalid-detail":
            with pytest.raises(ProviderError, match="invalid data"):
                get_show(shows[0].tvmaze_id)
        else:
            detail = get_show(shows[0].tvmaze_id)
            if scenario == "refreshed":
                assert detail["title"] == shows[0].title + " refreshed"
                assert detail["summary"] == "Updated provider snapshot."
            else:
                assert detail["title"] == shows[0].title
                assert (
                    detail["summary"] == "Local browser fixture & plain-text snapshot."
                )

    with patch(
        "shows.management.commands.discovery_demo.call_command",
        side_effect=verify_server,
    ):
        call_command("discovery_demo", scenario, stdout=StringIO())

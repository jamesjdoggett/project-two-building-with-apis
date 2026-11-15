from unittest.mock import MagicMock

import pytest
import requests
from django.utils import timezone

from . import tvmaze
from .models import Entry


@pytest.fixture(autouse=True)
def fresh_request_gate(monkeypatch):
    monkeypatch.setattr(tvmaze, "request_gate", tvmaze.RequestGate())


@pytest.fixture
def show_payload():
    return {
        "id": 180,
        "name": "Firefly",
        "url": "https://www.tvmaze.com/shows/180/firefly",
        "premiered": "2002-09-20",
        "summary": "<p>A <b>space</b> adventure &amp; friends.</p>",
        "image": {
            "medium": "https://static.tvmaze.com/uploads/images/medium_portrait/1.jpg"
        },
    }


@pytest.fixture
def provider_http(monkeypatch, show_payload):
    response = MagicMock(status_code=200, headers={})
    response.__enter__.return_value = response
    response.json.return_value = [{"show": show_payload}]

    def check_status():
        if response.status_code >= 400:
            raise requests.HTTPError(response=response)

    response.raise_for_status.side_effect = check_status
    get = MagicMock(return_value=response)
    monkeypatch.setattr(tvmaze.requests, "get", get)
    return get, response


@pytest.fixture
def viewer(django_user_model):
    return django_user_model.objects.create_user(
        username="viewer", password="Test-only-947!Moon"
    )


@pytest.fixture
def viewer_client(client, viewer):
    client.force_login(viewer)
    return client


@pytest.fixture
def entry_factory(viewer):
    def create(**overrides):
        values = {
            "owner": viewer,
            "tvmaze_id": 180,
            "title": "Firefly",
            "source_url": "https://www.tvmaze.com/shows/180/firefly",
            "summary": "A saved local summary.",
            "retrieved_at": timezone.now(),
        }
        return Entry.objects.create(**(values | overrides))

    return create

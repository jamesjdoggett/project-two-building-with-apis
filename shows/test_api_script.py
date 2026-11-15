"""Exercise the standalone HTTP client against Django's temporary live server."""

import secrets
from unittest.mock import Mock

import pytest
import requests

from scripts.test_showvault_api import ClientError, ShowVaultClient, explore


@pytest.mark.django_db(transaction=True)
def test_real_session_csrf_pagination_and_single_field_patch(
    live_server, viewer, entry_factory, django_user_model, monkeypatch, capsys
):
    password = secrets.token_urlsafe(24)
    viewer.set_password(password)
    viewer.save()
    entry = entry_factory(title="Alpha", rating=3, notes="Keep these notes")
    for index in range(21):
        entry_factory(tvmaze_id=1000 + index, title=f"Bravo {index:02}")
    other = django_user_model.objects.create_user(username="someone_else")
    foreign = entry_factory(owner=other, tvmaze_id=9999, title="Private")
    client = ShowVaultClient(live_server.url)
    try:
        with pytest.raises(ClientError, match="permission denied"):
            client.list_entries()
        with pytest.raises(ClientError, match="credentials rejected"):
            client.login(viewer.username, "incorrect")
        client.login(viewer.username, password)
        first = client.list_entries()
        assert first["count"] == 22
        assert first["next"] == 2
        assert len(client.list_entries(2)["results"]) == 2
        assert client.list_entries(query="Alpha")["count"] == 1
        with pytest.raises(ClientError, match="not owned"):
            client.detail(foreign.pk)
        with pytest.raises(ClientError, match=r"rejected \(400\)"):
            client.api("PATCH", f"/api/entries/{entry.pk}/", json={"rating": 11})
        rejected = client.request(
            "PATCH", f"/api/entries/{entry.pk}/", json={"rating": 9}
        )
        assert rejected.status_code == 403  # Session alone is insufficient for writes.
        # Drive the interactive path, including invalid ID and rating input.
        answers = iter(["bad", "999999", str(entry.pk), "11", "9"])
        monkeypatch.setattr("builtins.input", lambda _: next(answers))
        explore(client)
        output = capsys.readouterr().out
        assert "Before: rating = 3" in output
        assert "After (verified by GET): rating = 9" in output
        entry.refresh_from_db()
        assert entry.rating == 9
        assert entry.notes == "Keep these notes"
        assert entry.watch_status == "planned"
        assert entry.last_season is None
        assert entry.last_episode is None
        assert client.update_rating(entry.pk, None)["rating"] is None
        client.session.cookies.clear()
        with pytest.raises(ClientError, match="permission denied"):
            client.detail(entry.pk)
    finally:
        client.close()


@pytest.mark.parametrize(
    "failure, message",
    [(requests.Timeout(), "timed out"), (requests.ConnectionError(), "Cannot connect")],
)
def test_network_failures_have_safe_messages(failure, message):
    client = ShowVaultClient("http://127.0.0.1:8000")
    client.session.request = Mock(side_effect=failure)
    try:
        with pytest.raises(ClientError, match=message):
            client.list_entries()
    finally:
        client.close()


def test_empty_list_does_not_prompt_or_patch(capsys):
    client = Mock()
    client.list_entries.return_value = {
        "count": 0,
        "page": 1,
        "pages": 1,
        "next": None,
        "previous": None,
        "results": [],
    }
    explore(client)
    assert "No saved records match" in capsys.readouterr().out
    client.update_rating.assert_not_called()

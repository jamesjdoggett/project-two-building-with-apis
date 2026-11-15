"""Real competing saves on distinct SQLite connections, outside TestCase wraps."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import connections

from .models import Entry
from .operations import SaveBusy, save_entry


@pytest.mark.django_db(transaction=True)
def test_competing_saves_on_separate_connections_leave_one_unchanged_winner(
    django_user_model, monkeypatch
):
    owner = django_user_model.objects.create_user(username="concurrent-viewer")
    barrier = Barrier(2, timeout=10)
    connection_ids = []

    def fetch(_):
        connection = connections["default"]
        assert not connection.in_atomic_block  # Never wait on HTTP in a transaction.
        connection_ids.append(id(connection.connection))
        barrier.wait()  # Both saves have observed an absent entry before continuing.
        return {
            "title": "Concurrent snapshot",
            "source_url": "https://www.tvmaze.com/shows/180",
            "summary": "Saved once",
        }

    monkeypatch.setattr("shows.operations.get_show", fetch)

    def save(_):
        try:
            entry, created = save_entry(owner, 180)
            return ("created" if created else "existing", entry.pk)
        except SaveBusy:
            return ("busy", None)
        finally:
            connections["default"].close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(save, range(2)))

    assert len(set(connection_ids)) == 2
    assert sum(state == "created" for state, _ in outcomes) == 1
    winner = Entry.objects.get(owner=owner, tvmaze_id=180)
    assert winner.title == "Concurrent snapshot"
    original = Entry.objects.values().get(pk=winner.pk)
    assert all(state in {"created", "existing", "busy"} for state, _ in outcomes)
    monkeypatch.setattr(
        "shows.operations.get_show", lambda _: pytest.fail("Retry must stay local")
    )
    entry, created = save_entry(owner, 180)
    assert entry.pk == winner.pk and not created
    assert Entry.objects.count() == 1
    assert Entry.objects.values().get(pk=winner.pk) == original

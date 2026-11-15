import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone


@pytest.mark.django_db(transaction=True)
def test_existing_snapshots_gain_personal_defaults_without_metadata_changes():
    before_target = [("shows", "0001_initial")]
    after_target = [
        ("shows", "0003_entry_valid_personal_rating_entry_valid_watch_status_and_more")
    ]
    executor = MigrationExecutor(connection)
    executor.migrate(before_target)
    try:
        apps = executor.loader.project_state(before_target).apps
        user = apps.get_model("auth", "User").objects.create(username="existing")
        entries = apps.get_model("shows", "Entry").objects
        entry = entries.create(
            owner=user,
            tvmaze_id=180,
            title="Old snapshot",
            source_url="https://www.tvmaze.com/shows/180",
            summary="Keep this snapshot",
            retrieved_at=timezone.now(),
        )
        before = entries.values().get(pk=entry.pk)
        executor = MigrationExecutor(connection)
        executor.migrate(after_target)
        migrated_entries = (
            executor.loader.project_state(after_target)
            .apps.get_model("shows", "Entry")
            .objects
        )
        after = migrated_entries.values().get(pk=entry.pk)
        assert {key: after[key] for key in before} == before
        assert after["rating"] is None
        assert after["notes"] == ""
        assert after["watch_status"] == "planned"
        assert after["last_season"] is after["last_episode"] is None
    finally:
        MigrationExecutor(connection).migrate(after_target)

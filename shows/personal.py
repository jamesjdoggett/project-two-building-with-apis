"""Personal-state rules shared by website forms and future API serializers.

Callers parse input first, then validate the complete resulting personal state.
No rule infers status from a bookmark or changes a bookmark from status.
"""

from django.core.exceptions import ValidationError

PERSONAL_FIELDS = ("rating", "notes", "watch_status", "last_season", "last_episode")
WATCH_STATUSES = (
    ("planned", "Planned"),
    ("watching", "Watching"),
    ("paused", "Paused"),
    ("completed", "Completed"),
    ("dropped", "Dropped"),
)
MAX_NOTES_LENGTH = 5000
MAX_BOOKMARK_NUMBER = 9223372036854775807


def validate_personal_fields(values):
    """Raise field-specific errors for invalid, already-parsed personal values."""
    errors = {}
    rating = values["rating"]
    if rating is not None and (type(rating) is not int or not 1 <= rating <= 10):
        errors["rating"] = (
            "Enter a whole-number rating from 1 through 10, or leave blank."
        )
    notes = values["notes"]
    if not isinstance(notes, str) or len(notes) > MAX_NOTES_LENGTH:
        errors["notes"] = "Enter plain-text notes of at most 5,000 characters."
    if not isinstance(values["watch_status"], str) or values[
        "watch_status"
    ] not in dict(WATCH_STATUSES):
        errors["watch_status"] = "Choose a valid watch status."
    season, episode = values["last_season"], values["last_episode"]
    for field, value, minimum in (
        ("last_season", season, 0),
        ("last_episode", episode, 1),
    ):
        if value is not None and (
            type(value) is not int or not minimum <= value <= MAX_BOOKMARK_NUMBER
        ):
            errors[field] = (
                f"Enter a whole number from {minimum} through {MAX_BOOKMARK_NUMBER}."
            )
    if (season is None) != (episode is None):
        errors["last_season" if season is None else "last_episode"] = (
            "Enter both season and episode, or clear both to remove the bookmark."
        )
    if errors:
        raise ValidationError(errors)

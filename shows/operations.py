"""Shared authoritative save operations for website and future API callers."""

from django.db import OperationalError
from django.utils import timezone

from .models import Entry
from .tvmaze import get_show


class SaveBusy(Exception):
    """SQLite could not finish a competing save; safe to retry explicitly."""


def refresh_entry(owner, pk):
    entry = Entry.objects.get(owner=owner, pk=pk)
    snapshot = get_show(entry.tvmaze_id)
    # Update only provider fields; never save the stale personal values loaded
    # before HTTP. No write transaction spans the provider request.
    now = timezone.now()
    try:
        Entry.objects.filter(owner=owner, pk=pk).update(
            **snapshot, retrieved_at=now, updated_at=now
        )
    except OperationalError as exc:
        if "locked" not in str(exc).lower():
            raise
        raise SaveBusy(
            "The library is busy. Wait a moment, then try refreshing again."
        ) from None
    return Entry.objects.get(owner=owner, pk=pk)


def save_entry(owner, tvmaze_id):
    if type(tvmaze_id) is not int or not 1 <= tvmaze_id <= 9223372036854775807:
        raise ValueError("Enter a positive whole-number TVmaze show ID.")
    try:
        existing = Entry.objects.filter(owner=owner, tvmaze_id=tvmaze_id).first()
    except OperationalError as exc:
        if "locked" not in str(exc).lower():
            raise
        raise SaveBusy(
            "The library is busy. Wait a moment, then try saving again."
        ) from None
    if existing is not None:
        return existing, False
    # No transaction is held open during HTTP. get_or_create uses an atomic
    # insert and recovers unique collisions by returning the winning row.
    snapshot = get_show(tvmaze_id)
    try:
        return Entry.objects.get_or_create(
            owner=owner,
            tvmaze_id=tvmaze_id,
            defaults={"retrieved_at": timezone.now(), **snapshot},
        )
    except OperationalError as exc:
        if "locked" not in str(exc).lower():
            raise
        # SQLite can reject competing writers instead of waiting for uniqueness.
        # Return a committed winner when visible, otherwise offer a safe retry.
        try:
            existing = Entry.objects.filter(owner=owner, tvmaze_id=tvmaze_id).first()
        except OperationalError as read_exc:
            if "locked" not in str(read_exc).lower():
                raise
            existing = None
        if existing is not None:
            return existing, False
        raise SaveBusy(
            "The library is busy. Wait a moment, then try saving again."
        ) from None

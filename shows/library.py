"""Normalized, owner-scoped local queries for website and future API lists."""

from django.db.models import F
from django.db.models.functions import Lower

from .models import Entry
from .personal import WATCH_STATUSES

SORT_CHOICES = (
    ("recent", "Recently saved"),
    ("title", "Title A–Z"),
    ("rating", "Personal rating (highest first)"),
)


def library_entries(owner, params):
    query = params.get("q", "").strip()
    status = params.get("status", "").strip()
    sort = params.get("sort", "recent").strip()
    if status not in dict(WATCH_STATUSES):
        status = ""
    if sort not in dict(SORT_CHOICES):
        sort = "recent"
    entries = Entry.objects.filter(owner=owner)
    if query:
        entries = entries.filter(title__icontains=query)
    if status:
        entries = entries.filter(watch_status=status)
    ordering = {
        "recent": ("-created_at", "-pk"),
        "title": (Lower("title"), "pk"),
        "rating": (F("rating").desc(nulls_last=True), "-pk"),
    }
    return entries.order_by(*ordering[sort]), {
        "q": query,
        "status": status,
        "sort": sort,
    }

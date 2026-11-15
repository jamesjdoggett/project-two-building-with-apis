from urllib.parse import parse_qs, urlsplit

import pytest
from django.urls import reverse

from .models import Entry
from .personal import WATCH_STATUSES

pytestmark = pytest.mark.django_db


def test_combined_controls_are_private_stable_and_retained_across_pages(
    viewer_client, entry_factory, django_user_model, provider_http
):
    matches = [
        entry_factory(
            tvmaze_id=i + 1,
            title="Space & Friends",
            watch_status="paused",
            rating=10 if i < 2 else None,
        )
        for i in range(21)
    ]
    entry_factory(
        tvmaze_id=100, title="Space & Friends", watch_status="planned", rating=10
    )
    entry_factory(tvmaze_id=101, title="Other title", watch_status="paused", rating=10)
    other = django_user_model.objects.create_user(username="other")
    entry_factory(
        owner=other, title="Space & Friends", watch_status="paused", rating=10
    )
    provider_http[0].side_effect = AssertionError("Library controls must be local")
    params = {"q": "  sPaCe & fRiEnDs  ", "status": "paused", "sort": "rating"}
    first = viewer_client.get(reverse("shows:library"), params)
    assert first.context["page_obj"].paginator.count == 21
    expected = [matches[1], matches[0], *matches[:1:-1]]
    assert list(first.context["page_obj"]) == expected[:20]
    assert first.context["query"] == "sPaCe & fRiEnDs"
    # Follow the actual rendered pagination link, including its encoded ampersand.
    from html.parser import HTMLParser

    class Links(HTMLParser):
        def __init__(self):
            super().__init__()
            self.urls = []

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                self.urls.append(dict(attrs).get("href", ""))

    links = Links()
    links.feed(first.content.decode())
    next_url = next(url for url in links.urls if "page=2" in url)
    assert parse_qs(urlsplit(next_url).query) == {
        "q": ["sPaCe & fRiEnDs"],
        "status": ["paused"],
        "sort": ["rating"],
        "page": ["2"],
    }
    second = viewer_client.get(reverse("shows:library") + next_url)
    assert list(second.context["page_obj"]) == expected[20:]
    assert b'value="paused" selected' in second.content
    assert b'value="rating" selected' in second.content
    provider_http[0].assert_not_called()


@pytest.mark.parametrize(
    ("sort", "indices"),
    [
        ("recent", [5, 4, 3, 2, 1, 0]),
        ("title", [1, 2, 3, 5, 4, 0]),
        ("rating", [3, 2, 1, 5, 4, 0]),
    ],
)
def test_all_sort_orders_with_deterministic_ties_and_unrated_last(
    viewer_client, entry_factory, provider_http, sort, indices
):
    entries = [
        entry_factory(tvmaze_id=i + 1, title=title, rating=rating)
        for i, (title, rating) in enumerate(
            [
                ("zebra", None),
                ("alpha", 8),
                ("ALPHA", 8),
                ("Bravo", 10),
                ("unrated", None),
                ("low", 1),
            ]
        )
    ]
    Entry.objects.update(created_at=entries[0].created_at)
    page = viewer_client.get(reverse("shows:library"), {"sort": sort})
    assert list(page.context["page_obj"]) == [entries[i] for i in indices]
    assert page.context["selected_sort"] == sort
    provider_http[0].assert_not_called()


@pytest.mark.parametrize("status", [value for value, _ in WATCH_STATUSES])
def test_each_status_filter_with_trimmed_case_insensitive_title_search(
    viewer_client, entry_factory, django_user_model, provider_http, status
):
    entries = [
        entry_factory(tvmaze_id=i + 1, title="Mixed TITLE", watch_status=value)
        for i, (value, _) in enumerate(WATCH_STATUSES)
    ]
    other = django_user_model.objects.create_user(username="other", is_staff=True)
    entry_factory(owner=other, title="Mixed TITLE", watch_status=status)
    for user, expected in (
        (
            entries[0].owner,
            [entry for entry in entries if entry.watch_status == status],
        ),
        (other, list(Entry.objects.filter(owner=other))),
    ):
        viewer_client.force_login(user)
        response = viewer_client.get(
            reverse("shows:library"), {"q": "  miXeD tItLe  ", "status": status}
        )
        assert list(response.context["page_obj"]) == expected
        assert response.context["query"] == "miXeD tItLe"
    provider_http[0].assert_not_called()


@pytest.mark.parametrize(
    ("params", "query", "status", "sort"),
    [
        ({}, "", "", "recent"),
        ({"q": "  ", "status": "bogus", "sort": "bogus"}, "", "", "recent"),
        (
            {"q": "  Fire  ", "status": " paused ", "sort": " title "},
            "Fire",
            "paused",
            "title",
        ),
        ({"status": "Completed", "sort": "TITLE"}, "", "", "recent"),
    ],
)
def test_query_normalization(
    viewer_client, entry_factory, provider_http, params, query, status, sort
):
    entry_factory(watch_status="paused")
    response = viewer_client.get(reverse("shows:library"), params)
    assert response.context["query"] == query
    assert response.context["selected_status"] == status
    assert response.context["selected_sort"] == sort
    assert parse_qs(response.context["pagination_query"], keep_blank_values=True) == {
        "q": [query],
        "status": [status],
        "sort": [sort],
    }
    provider_http[0].assert_not_called()


@pytest.mark.parametrize(
    ("page", "expected"), [("bad", 1), ("1.5", 1), ("0", 2), ("-1", 2), ("9999", 2)]
)
def test_forgiving_pages_preserve_combined_controls(
    viewer_client, entry_factory, provider_http, page, expected
):
    for i in range(21):
        entry_factory(tvmaze_id=i + 1, watch_status="completed", title="My title")
    response = viewer_client.get(
        reverse("shows:library"),
        {"q": "title", "status": "completed", "sort": "title", "page": page},
    )
    assert response.context["page_obj"].number == expected
    assert response.context["page_obj"].paginator.count == 21
    assert response.context["query"] == "title"
    assert response.context["selected_status"] == "completed"
    assert response.context["selected_sort"] == "title"
    provider_http[0].assert_not_called()


def test_empty_library_differs_from_no_owned_matches(
    viewer_client, entry_factory, django_user_model, provider_http
):
    other = django_user_model.objects.create_user(username="other")
    entry_factory(owner=other)
    url = reverse("shows:library")
    empty = viewer_client.get(url, {"q": "Firefly"})
    assert b"Your library is empty" in empty.content
    assert b"No saved shows match" not in empty.content
    entry_factory(title="Different title")
    no_match = viewer_client.get(url, {"q": "Firefly"})
    assert b"No saved shows match" in no_match.content
    assert b"Your library is empty" not in no_match.content
    assert b"reset your filters" in no_match.content
    provider_http[0].assert_not_called()

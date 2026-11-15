import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse

from .models import Entry
from .personal import PERSONAL_FIELDS, WATCH_STATUSES, validate_personal_fields

pytestmark = pytest.mark.django_db


def personal_data(**overrides):
    return {
        "rating": "7",
        "notes": "Private note",
        "watch_status": "watching",
        "last_season": "2",
        "last_episode": "4",
        **overrides,
    }


def test_invalid_personal_edit_preserves_all_saved_values(
    viewer_client, entry_factory, provider_http
):
    entry = entry_factory(
        rating=7,
        notes="Keep this\nprivate note",
        watch_status="paused",
        last_season=2,
        last_episode=4,
    )
    before = Entry.objects.values().get(pk=entry.pk)
    provider_http[0].side_effect = AssertionError("Edits must not contact TVmaze")
    response = viewer_client.post(
        reverse("shows:edit", args=[entry.pk]),
        {
            "rating": "11",
            "notes": "Do not partially save this",
            "watch_status": "completed",
            "last_season": "3",
            "last_episode": "8",
        },
    )
    assert response.status_code == 400
    assert "rating" in response.context["form"].errors
    assert b"1 through 10" in response.content
    assert Entry.objects.values().get(pk=entry.pk) == before
    provider_http[0].assert_not_called()


@pytest.mark.parametrize(
    ("changes", "error_field"),
    [
        ({"rating": "0"}, "rating"),
        ({"rating": "11"}, "rating"),
        ({"rating": "1.5"}, "rating"),
        ({"notes": "n" * 5001}, "notes"),
        ({"notes": " " * 5001}, "notes"),
        ({"watch_status": "invalid"}, "watch_status"),
        ({"last_season": "-1"}, "last_season"),
        ({"last_season": "1.5"}, "last_season"),
        ({"last_episode": "0"}, "last_episode"),
        ({"last_episode": "2.5"}, "last_episode"),
        ({"last_season": ""}, "last_season"),
        ({"last_episode": ""}, "last_episode"),
        ({"last_season": str(2**63)}, "last_season"),
        ({"last_episode": str(2**63)}, "last_episode"),
    ],
)
def test_personal_validation_boundaries_do_not_partially_save(
    viewer_client, entry_factory, provider_http, changes, error_field
):
    entry = entry_factory(
        rating=8,
        notes="Original\nnotes",
        watch_status="completed",
        last_season=3,
        last_episode=8,
    )
    before = Entry.objects.values().get(pk=entry.pk)
    response = viewer_client.post(
        reverse("shows:edit", args=[entry.pk]), personal_data(**changes)
    )
    assert response.status_code == 400
    assert error_field in response.context["form"].errors
    assert b"Nothing was saved" in response.content
    assert Entry.objects.values().get(pk=entry.pk) == before
    provider_http[0].assert_not_called()


@pytest.mark.parametrize(
    ("rating", "notes", "season", "episode"),
    [
        ("", "", "", ""),
        ("1", "n" * 5000, "0", "1"),
        ("10", '  <script>alert("private")</script>\nSecond line  ', "4", "10"),
        ("10", " " * 5000, "2", "4"),
    ],
)
def test_valid_personal_edits_preserve_snapshot_and_render_plain_text(
    viewer_client, entry_factory, provider_http, rating, notes, season, episode
):
    entry = entry_factory()
    before = Entry.objects.values().get(pk=entry.pk)
    response = viewer_client.post(
        reverse("shows:edit", args=[entry.pk]),
        personal_data(
            rating=rating,
            notes=notes,
            last_season=season,
            last_episode=episode,
        ),
    )
    assert response.status_code == 302
    after = Entry.objects.values().get(pk=entry.pk)
    assert after["rating"] == (int(rating) if rating else None)
    assert after["notes"] == notes
    assert after["watch_status"] == "watching"
    assert after["last_season"] == (int(season) if season else None)
    assert after["last_episode"] == (int(episode) if episode else None)
    assert after["updated_at"] >= before["updated_at"]
    for field in before.keys() - {*PERSONAL_FIELDS, "updated_at"}:
        assert after[field] == before[field]
    detail = viewer_client.get(response.url)
    assert b"Your viewing details were saved" in detail.content
    assert b"Edit viewing details" in detail.content
    if "<script>" in notes:
        assert b"&lt;script&gt;" in detail.content
        assert b'<script>alert("private")' not in detail.content
        assert b"\nSecond line  " in detail.content
    if season == "0":
        assert b"S0 E1" in detail.content
    form_page = viewer_client.get(reverse("shows:edit", args=[entry.pk]))
    assert form_page.context["form"].initial["notes"] == notes
    assert form_page.context["form"].initial["rating"] == after["rating"]
    # Re-saving through discovery must preserve the newly editable state too.
    duplicate = viewer_client.post(reverse("shows:save", args=[entry.tvmaze_id]))
    assert duplicate.url == response.url
    assert Entry.objects.values().get(pk=entry.pk) == after
    provider_http[0].assert_not_called()


@pytest.mark.parametrize("status", [value for value, _ in WATCH_STATUSES])
def test_each_status_is_independent_of_bookmark_save_correct_and_clear(
    viewer_client, entry_factory, provider_http, status
):
    entry = entry_factory(watch_status="watching", last_season=4, last_episode=10)
    url = reverse("shows:edit", args=[entry.pk])
    # Choosing a status retains the existing bookmark, including Planned.
    for season, episode, clear, expected in [
        (4, 10, False, (4, 10)),
        (0, 1, False, (0, 1)),
        (2, 3, False, (2, 3)),
        (2, 3, True, (None, None)),
    ]:
        response = viewer_client.post(
            url,
            personal_data(
                watch_status=status,
                last_season=season,
                last_episode=episode,
                **({"clear_bookmark": "on"} if clear else {}),
            ),
        )
        assert response.status_code == 302
        entry.refresh_from_db()
        assert entry.watch_status == status
        assert (entry.last_season, entry.last_episode) == expected
    provider_http[0].assert_not_called()


@pytest.mark.parametrize("privilege", ["ordinary", "staff", "superuser"])
def test_foreign_and_missing_edit_are_404_even_for_privileged_users(
    viewer_client, entry_factory, django_user_model, privilege, provider_http
):
    entry = entry_factory(rating=7)
    before = Entry.objects.values().get(pk=entry.pk)
    other = django_user_model.objects.create_user(
        username="other",
        is_staff=privilege != "ordinary",
        is_superuser=privilege == "superuser",
    )
    viewer_client.force_login(other)
    for pk in (entry.pk, 999999):
        url = reverse("shows:edit", args=[pk])
        assert viewer_client.get(url).status_code == 404
        assert viewer_client.post(url, personal_data()).status_code == 404
    assert Entry.objects.values().get(pk=entry.pk) == before
    provider_http[0].assert_not_called()


def test_edit_requires_login_post_and_csrf_and_get_changes_nothing(
    viewer_client, viewer, entry_factory, provider_http
):
    entry = entry_factory()
    url = reverse("shows:edit", args=[entry.pk])
    before = Entry.objects.values().get(pk=entry.pk)
    anonymous = Client()
    for method in ("get", "post"):
        response = getattr(anonymous, method)(url)
        assert response.status_code == 302
        assert response.url.startswith(reverse("login") + "?next=")
    get = viewer_client.get(url, personal_data(rating="10"))
    assert get.status_code == 200
    assert b"Cancel" in get.content
    for method in ("put", "patch", "delete"):
        assert getattr(viewer_client, method)(url).status_code == 405
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(viewer)
    assert csrf_client.post(url, personal_data()).status_code == 403
    assert Entry.objects.values().get(pk=entry.pk) == before
    csrf_client.get(url)
    response = csrf_client.post(
        url, personal_data(), HTTP_X_CSRFTOKEN=csrf_client.cookies["csrftoken"].value
    )
    assert response.status_code == 302
    entry.refresh_from_db()
    assert entry.rating == 7
    provider_http[0].assert_not_called()


def test_edit_rejects_every_nonpersonal_model_field_and_other_overrides(
    viewer_client, entry_factory, provider_http
):
    entry = entry_factory()
    before = Entry.objects.values().get(pk=entry.pk)
    url = reverse("shows:edit", args=[entry.pk])
    forbidden = {field.name for field in Entry._meta.fields} - set(PERSONAL_FIELDS)
    for field in forbidden | {"owner_id", "url", "unexpected"}:
        response = viewer_client.post(url, personal_data(**{field: "forged"}))
        assert response.status_code == 400, field
        assert b"Only personal viewing fields" in response.content
        assert Entry.objects.values().get(pk=entry.pk) == before
    assert (
        viewer_client.post(
            url, personal_data(), content_type="application/json"
        ).status_code
        == 400
    )
    assert viewer_client.post(url + "?owner=1", personal_data()).status_code == 400
    assert Entry.objects.values().get(pk=entry.pk) == before
    provider_http[0].assert_not_called()


@pytest.mark.parametrize(
    "changes",
    [
        {"rating": 0},
        {"rating": 11},
        {"watch_status": "invalid"},
        {"last_season": -1, "last_episode": 1},
        {"last_season": 0, "last_episode": 0},
        {"last_season": 2, "last_episode": None},
        {"last_season": None, "last_episode": 3},
    ],
)
def test_database_rejects_invalid_numeric_status_and_pair_updates(
    entry_factory, changes
):
    entry = entry_factory()
    before = Entry.objects.values().get(pk=entry.pk)
    with pytest.raises(IntegrityError), transaction.atomic():
        Entry.objects.filter(pk=entry.pk).update(**changes)
    assert Entry.objects.values().get(pk=entry.pk) == before


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("rating", True),
        ("rating", 1.5),
        ("rating", "5"),
        ("notes", None),
        ("watch_status", []),
        ("last_season", False),
        ("last_episode", 1.5),
    ],
)
def test_shared_rules_reject_wrong_parsed_types(field, value):
    values = dict(
        rating=None,
        notes="",
        watch_status="planned",
        last_season=None,
        last_episode=None,
    )
    with pytest.raises(ValidationError) as error:
        validate_personal_fields({**values, field: value})
    assert field in error.value.message_dict


def test_independent_bookmark_corrections_rewatch_and_clear_are_visible(
    viewer_client, entry_factory, provider_http
):
    entry = entry_factory(watch_status="completed", last_season=3, last_episode=8)
    provider_http[0].side_effect = AssertionError("Progress must remain local")
    edit_url = reverse("shows:edit", args=[entry.pk])
    for status, season, episode, clear, expected_bookmark in (
        ("completed", 3, 7, False, (3, 7)),
        ("paused", 3, 7, False, (3, 7)),
        ("paused", 2, 4, False, (2, 4)),
        ("completed", 2, 4, False, (2, 4)),
        ("planned", 2, 4, False, (2, 4)),
        ("planned", 2, 4, True, (None, None)),
    ):
        response = viewer_client.post(
            edit_url,
            {
                "rating": "",
                "notes": "",
                "watch_status": status,
                "last_season": season,
                "last_episode": episode,
                **({"clear_bookmark": "on"} if clear else {}),
            },
            follow=True,
        )
        assert response.status_code == 200
        entry.refresh_from_db()
        assert entry.watch_status == status
        assert (entry.last_season, entry.last_episode) == expected_bookmark
        assert f"<dd>{status.title()}</dd>".encode() in response.content
        if clear:
            assert b"No bookmark set." in response.content
        else:
            assert f"S{season} E{episode}".encode() in response.content
    provider_http[0].assert_not_called()

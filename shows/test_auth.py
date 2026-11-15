import pytest
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("route", ["shows:home", "shows:discover"])
def test_anonymous_pages_require_login_without_provider_call(
    client, provider_http, route
):
    response = client.get(reverse(route))
    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={reverse(route)}"
    provider_http[0].assert_not_called()


def test_ordinary_user_can_sign_in_and_sign_out(client, viewer):
    assert not viewer.is_staff
    response = client.post(
        reverse("login"),
        {"username": viewer.username, "password": "Test-only-947!Moon"},
    )
    assert response.status_code == 302
    assert response.url == reverse("shows:home")
    home = client.get(response.url)
    assert home.status_code == 200
    assert b"Welcome, viewer" in home.content
    assert b"Discover shows" in home.content
    assert b"Sign out" in home.content
    assert client.get(reverse("shows:discover")).status_code == 200
    response = client.post(reverse("logout"))
    assert response.status_code == 302
    assert response.url == reverse("login")
    assert "_auth_user_id" not in client.session


@pytest.mark.parametrize("inactive", [False, True])
def test_invalid_credentials_or_inactive_account_cannot_sign_in(
    client, viewer, inactive
):
    if inactive:
        viewer.is_active = False
        viewer.save()
    response = client.post(
        reverse("login"),
        {
            "username": viewer.username,
            "password": "Test-only-947!Moon" if inactive else "wrong-password",
        },
    )
    assert response.status_code == 200
    assert response.context["form"].non_field_errors()
    assert b'role="alert"' in response.content
    assert "_auth_user_id" not in client.session


@pytest.mark.parametrize("next_url", ["/discover/?q=Firefly", "https://example.com/"])
def test_login_accepts_only_safe_next_redirects(client, viewer, next_url):
    response = client.post(
        reverse("login"),
        {
            "username": viewer.username,
            "password": "Test-only-947!Moon",
            "next": next_url,
        },
    )
    expected = next_url if next_url.startswith("/") else reverse("shows:home")
    assert response.status_code == 302
    assert response.url == expected


def test_login_and_logout_enforce_csrf_and_logout_requires_post(viewer):
    client = Client(enforce_csrf_checks=True)
    data = {"username": viewer.username, "password": "Test-only-947!Moon"}
    assert client.post(reverse("login"), data).status_code == 403
    client.get(reverse("login"))
    data["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
    assert client.post(reverse("login"), data).status_code == 302
    assert client.get(reverse("logout")).status_code == 405
    assert client.post(reverse("logout")).status_code == 403
    assert "_auth_user_id" in client.session
    client.get(reverse("shows:home"))
    response = client.post(
        reverse("logout"), {"csrfmiddlewaretoken": client.cookies["csrftoken"].value}
    )
    assert response.status_code == 302
    assert "_auth_user_id" not in client.session


def test_admin_can_create_two_ordinary_accounts(
    admin_client, client, django_user_model
):
    for username in ("first-viewer", "second-viewer"):
        response = admin_client.post(
            reverse("admin:auth_user_add"),
            {
                "username": username,
                "usable_password": "true",
                "password1": "Test-only-583!Forest",
                "password2": "Test-only-583!Forest",
                "_save": "Save",
            },
        )
        assert response.status_code == 302
        user = django_user_model.objects.get(username=username)
        assert user.is_active and not user.is_staff and not user.is_superuser
        response = client.post(
            reverse("login"), {"username": username, "password": "Test-only-583!Forest"}
        )
        assert response.status_code == 302
        assert client.get(reverse("shows:home")).status_code == 200
        assert client.get(reverse("admin:index")).status_code == 302
        assert client.get(reverse("admin:auth_user_add")).status_code == 302
        client.post(reverse("logout"))


def test_phase_one_has_no_public_signup_or_unfinished_actions(viewer_client):
    assert viewer_client.get("/accounts/signup/").status_code == 404
    response = viewer_client.get(reverse("shows:home"))
    assert b'href="/library/' not in response.content


@pytest.mark.parametrize("route", ["shows:home", "shows:discover"])
def test_discovery_and_home_are_read_only(viewer_client, provider_http, route):
    assert viewer_client.post(reverse(route)).status_code == 405
    provider_http[0].assert_not_called()

"""Explore the local ShowVault API; optionally PATCH one saved show's rating.

Run: uv run python scripts/test_showvault_api.py
Credentials: SHOWVAULT_USERNAME / SHOWVAULT_PASSWORD, or interactive prompts.
Uses only requests and the standard library; never imports Django or queries SQLite.
"""

import argparse
import getpass
import json
import os
import sys
from urllib.parse import urlsplit

import requests


class ClientError(Exception):
    """A safe, user-facing failure message."""


class ShowVaultClient:
    def __init__(self, base_url, timeout=10):
        parsed = urlsplit(base_url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ClientError("Use a local HTTP origin, e.g. http://127.0.0.1:8000")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["Accept"] = "application/json"

    def close(self):
        self.session.close()

    def request(self, method, path, **kwargs):
        try:
            return self.session.request(
                method,
                self.base_url + path,
                timeout=self.timeout,
                allow_redirects=False,
                **kwargs,
            )
        except requests.Timeout:
            raise ClientError(
                "Request timed out. If this was PATCH, it may have succeeded; "
                "check the saved rating before retrying."
            ) from None
        except requests.ConnectionError:
            raise ClientError(
                "Cannot connect to ShowVault. Check the address and start runserver. "
                "If PATCH was interrupted, check the rating before retrying."
            ) from None
        except requests.RequestException:
            raise ClientError("HTTP request failed; check the local server.") from None

    def csrf(self):
        token = self.session.cookies.get("csrftoken")
        if not token:
            raise ClientError("No CSRF cookie received from ShowVault.")
        return token

    def login(self, username, password):
        path = "/accounts/login/"
        response = self.request("GET", path)
        if response.status_code != 200:
            raise ClientError("Could not open the ShowVault login page.")
        response = self.request(
            "POST",
            path,
            data={
                "username": username,
                "password": password,
                "csrfmiddlewaretoken": self.csrf(),
            },
            headers={"Referer": self.base_url + path},
        )
        if response.status_code == 200:
            raise ClientError("Login failed: credentials rejected or account inactive.")
        if response.status_code != 302 or not self.session.cookies.get("sessionid"):
            raise ClientError("Login failed: expected a session cookie and redirect.")
        # Login rotates Django's CSRF token. Read the current cookie on every write.
        self.csrf()

    def api(self, method, path, **kwargs):
        if method == "PATCH":
            kwargs["headers"] = {
                "X-CSRFToken": self.csrf(),
                "Referer": self.base_url + "/",
            }
        response = self.request(method, path, **kwargs)
        if response.status_code in {401, 403}:
            raise ClientError(
                "Authentication or permission denied (401/403). Sign in again; "
                "PATCH also requires a valid CSRF token."
            )
        if response.status_code == 404:
            raise ClientError("Entry not found or not owned by this account (404).")
        if response.status_code == 400:
            raise ClientError("Request rejected (400): check the rating and input.")
        if response.status_code != 200:
            raise ClientError(f"API request failed (HTTP {response.status_code}).")
        try:
            data = response.json()
        except ValueError:
            raise ClientError(
                "Expected JSON; check the ShowVault server address."
            ) from None
        if not isinstance(data, dict):
            raise ClientError("Unexpected API response: expected a JSON object.")
        return data

    def list_entries(self, page=1, query=""):
        data = self.api(
            "GET", "/api/entries/", params={"sort": "title", "page": page, "q": query}
        )
        if not {"results", "count", "page", "pages", "next", "previous"} <= data.keys():
            raise ClientError("Unexpected list response: missing pagination fields.")
        return data

    def detail(self, entry_id):
        data = self.api("GET", f"/api/entries/{entry_id}/")
        if not {"id", "title", "rating"} <= data.keys():
            raise ClientError("Unexpected entry response: missing entry fields.")
        return data

    def update_rating(self, entry_id, rating):
        if rating is not None and (type(rating) is not int or not 1 <= rating <= 10):
            raise ClientError("Rating must be a whole number from 1 to 10, or null.")
        self.api("PATCH", f"/api/entries/{entry_id}/", json={"rating": rating})
        after = self.detail(entry_id)
        if after["rating"] != rating:
            raise ClientError(
                "PATCH returned success, but GET did not confirm the requested rating. "
                "Another client may have edited this entry."
            )
        return after


def display_page(data):
    print(
        f"\nPage {data['page']} of {data['pages']} | {data['count']} saved records "
        f"| previous: {data['previous']} | next: {data['next']}"
    )
    print("Sorted by title; IDs below are local saved-entry IDs.")
    for row in data["results"]:
        # JSON escaping keeps record text from injecting terminal control characters.
        print(
            f"  ID {row['id']} | {json.dumps(row['title'], ensure_ascii=True)} "
            f"| status: {row['watch_status']} | rating: {row['rating']}"
        )


def explore(client, query="", list_only=False):
    page = 1
    while True:
        data = client.list_entries(page, query)
        display_page(data)
        if not data["results"]:
            print("No saved records match. Save a show on the website or change --q.")
            return
        if list_only:
            return
        choice = input("Entry ID on this page, n/p for pages, or q to quit: ").strip()
        if choice.lower() == "q":
            return
        if choice.lower() in {"n", "p"}:
            target = data["next" if choice.lower() == "n" else "previous"]
            if target is None:
                print("No page in that direction.")
            else:
                page = target
            continue
        try:
            entry_id = int(choice)
        except ValueError:
            print("Enter a displayed numeric ID, n, p, or q.")
            continue
        if entry_id not in {row["id"] for row in data["results"]}:
            print("Select an ID from the current page.")
            continue
        before = client.detail(entry_id)
        print(f"Before: rating = {before['rating']}")
        while True:
            raw = input("New rating (1-10, null to clear, or q to cancel): ").strip()
            if raw.lower() == "q":
                return
            try:
                rating = None if raw.lower() == "null" else int(raw)
            except ValueError:
                print("Enter a whole number from 1 to 10, null, or q.")
                continue
            if rating is not None and not 1 <= rating <= 10:
                print("Rating must be from 1 to 10.")
                continue
            if rating == before["rating"]:
                print("Choose a different rating so the update demonstrates a change.")
                continue
            break
        after = client.update_rating(entry_id, rating)
        print(f"After (verified by GET): rating = {after['rating']}")
        print("Updated rating only; the server also maintains updated_at.")
        return


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--q", default="", help="Filter saved titles by substring")
    parser.add_argument("--list-only", action="store_true", help="GET without editing")
    args = parser.parse_args()
    client = None
    try:
        client = ShowVaultClient(args.base_url)
        username = os.environ.get("SHOWVAULT_USERNAME") or input("Username: ").strip()
        if not username:
            raise ClientError("Username cannot be empty.")
        password = os.environ.get("SHOWVAULT_PASSWORD") or getpass.getpass("Password: ")
        if not password:
            raise ClientError("Password cannot be empty.")
        client.login(username, password)
        del password
        explore(client, args.q, args.list_only)
        return 0
    except EOFError, KeyboardInterrupt:
        print("\nCancelled. If PATCH was in flight, check the rating before retrying.")
        return 130
    except ClientError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    sys.exit(main())

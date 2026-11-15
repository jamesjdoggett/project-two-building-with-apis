"""Search TVmaze from the console; run with uv run scripts/test_tvmaze_api.py."""

import argparse
import math
import sys
import textwrap
from html.parser import HTMLParser

import requests

SEARCH_URL = "https://api.tvmaze.com/search/shows"
DISPLAY_LIMIT = 5


class SummaryParser(HTMLParser):
    """Collect plain text from TVmaze's HTML summaries."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in {"p", "br", "div"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"p", "div"}:
            self.parts.append(" ")


def plain_summary(summary):
    parser = SummaryParser()
    parser.feed(summary or "")
    return " ".join("".join(parser.parts).split()) or "No summary available."


def search_shows(phrase, url, timeout):
    """Fetch JSON and validate the fields this script needs before displaying it."""
    with requests.get(
        url,
        params={"q": phrase},
        timeout=timeout,
        headers={"User-Agent": "ProjectTwo-TVmazeConsole/0.1"},
    ) as response:
        response.raise_for_status()
        results = response.json()

    if not isinstance(results, list):
        raise TypeError("Expected a list of search matches.")

    shows = []
    for result in results:
        show = result.get("show") if isinstance(result, dict) else None
        if not isinstance(show, dict) or not isinstance(show.get("name"), str):
            raise TypeError("A search match is missing a valid show title.")
        for field in ("premiered", "summary"):
            if show.get(field) is not None and not isinstance(show[field], str):
                raise ValueError(f"A show has an invalid {field} field.")
        genres = show.get("genres")
        if genres is not None and (
            not isinstance(genres, list)
            or any(not isinstance(genre, str) for genre in genres)
        ):
            raise ValueError("A show has an invalid genres field.")
        shows.append(show)
    return shows


def display_shows(shows):
    print(f"\nFound {len(shows)} matches; showing {min(len(shows), DISPLAY_LIMIT)}.")
    print("Source: TVmaze (https://www.tvmaze.com), CC BY-SA 4.0.")
    print("License: https://creativecommons.org/licenses/by-sa/4.0/")
    print("Summaries converted from HTML to plain text.\n")
    for number, show in enumerate(shows[:DISPLAY_LIMIT], start=1):
        print(f"{number}. {show['name']}")
        print(f"   Premiered: {show.get('premiered') or 'Unknown'}")
        print(f"   Genres: {', '.join(show.get('genres') or []) or 'Not listed'}")
        print("   Summary:")
        print(
            textwrap.fill(
                plain_summary(show.get("summary")),
                width=88,
                initial_indent="      ",
                subsequent_indent="      ",
            )
        )
        print()


def positive_timeout(value):
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("timeout must be a positive, finite number")
    return seconds


def main():
    parser = argparse.ArgumentParser(description="Search TVmaze for TV shows.")
    parser.add_argument(
        "--url", default=SEARCH_URL, help="Search URL override for testing"
    )
    parser.add_argument(
        "--timeout",
        type=positive_timeout,
        default=10.0,
        help="Connection/read timeout in seconds (default: 10)",
    )
    args = parser.parse_args()

    try:
        phrase = input("Search for a TV show: ").strip()
    except EOFError, KeyboardInterrupt:
        print("\nSearch cancelled: no input provided.", file=sys.stderr)
        return 1
    if not phrase:
        print(
            "Enter a show title or search phrase; the search cannot be empty.",
            file=sys.stderr,
        )
        return 1

    try:
        shows = search_shows(phrase, args.url, args.timeout)
    except requests.Timeout:
        message = "The request timed out. Try again or increase --timeout."
    except requests.ConnectionError:
        message = "Could not connect. Check your internet connection and the API URL."
    except requests.HTTPError as error:
        message = (
            f"HTTP error {error.response.status_code}. "
            "Check the URL or try again later."
        )
    except requests.exceptions.JSONDecodeError:
        message = "Invalid response: the server did not return valid JSON."
    except requests.RequestException:
        message = "The request failed. Check the API URL and try again."
    except ValueError, TypeError:
        message = (
            "Invalid response: expected TVmaze search JSON with valid show fields."
        )
    else:
        if shows:
            display_shows(shows)
        else:
            print(f"No shows found for {phrase!r}. Try a different title.")
        return 0

    print(message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    # TVmaze can return international titles even when stdout is piped on Windows.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

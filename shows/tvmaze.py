"""Official TVmaze search, validation, and a shared single-process request gate."""

import math
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from threading import Lock
from urllib.parse import urlsplit

import requests

SEARCH_URL = "https://api.tvmaze.com/search/shows"
USER_AGENT = "ShowVault/0.1 (personal TV tracker)"


class ProviderError(Exception):
    """A safe, actionable message suitable for the discovery page."""


class RateLimited(ProviderError):
    def __init__(self, seconds):
        self.retry_after = max(1, math.ceil(seconds))
        unit = "second" if self.retry_after == 1 else "seconds"
        super().__init__(
            f"TVmaze requests are temporarily limited. Wait {self.retry_after} "
            f"{unit}, then try again."
        )


class RequestGate:
    """At most one request/second across threads/users in the local server.

    Reject early requests rather than sleeping or automatically retrying. A
    provider 429 extends this same gate using its Retry-After guidance.
    """

    def __init__(self):
        self._lock = Lock()
        self._next_allowed = 0.0

    def acquire(self):
        with self._lock:
            now = time.monotonic()
            if now < self._next_allowed:
                raise RateLimited(self._next_allowed - now)
            self._next_allowed = now + 1

    def defer(self, seconds):
        with self._lock:
            self._next_allowed = max(self._next_allowed, time.monotonic() + seconds)


request_gate = RequestGate()


def retry_after_seconds(value):
    """Accept Retry-After delta seconds or HTTP dates; default to ten seconds."""
    try:
        return max(1, int(value))
    except TypeError, ValueError:
        try:
            until = parsedate_to_datetime(value)
            return max(
                1, math.ceil((until - datetime.now(timezone.utc)).total_seconds())
            )
        except TypeError, ValueError, OverflowError:
            return 10


class SummaryParser(HTMLParser):
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


@dataclass(frozen=True)
class SearchShow:
    tvmaze_id: int
    title: str
    premiere_year: int | None
    summary: str
    poster_url: str
    source_url: str


def web_url(value):
    if not isinstance(value, str):
        raise ValueError("Invalid URL")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Invalid URL")
    return value


def parse_show(show):
    if not isinstance(show, dict):
        raise ValueError("Missing show")
    show_id, title = show.get("id"), show.get("name")
    if type(show_id) is not int or show_id < 1:
        raise ValueError("Invalid ID")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Missing title")
    source = web_url(show.get("url"))
    if urlsplit(source).hostname not in {"www.tvmaze.com", "tvmaze.com"}:
        raise ValueError("Invalid source")

    premiered = show.get("premiered")
    year = date.fromisoformat(premiered).year if premiered else None
    summary = show.get("summary")
    if summary is not None and not isinstance(summary, str):
        raise ValueError("Invalid summary")
    parser = SummaryParser()
    parser.feed(summary or "")
    text = " ".join("".join(parser.parts).split()) or "No summary available."

    image = show.get("image")
    poster = ""
    if image is not None:
        if not isinstance(image, dict):
            raise ValueError("Invalid image")
        poster = image.get("medium") or image.get("original") or ""
        if poster:
            poster = web_url(poster)
    return SearchShow(show_id, title.strip(), year, text, poster, source)


def search_shows(query):
    """Fetch all search results in provider order; never auto-retry."""
    query = query.strip()
    if not query:
        return []
    request_gate.acquire()
    try:
        with requests.get(
            SEARCH_URL,
            params={"q": query},
            headers={"User-Agent": USER_AGENT},
            timeout=(10, 10),
            allow_redirects=False,
        ) as response:
            if response.status_code == 429:
                seconds = retry_after_seconds(response.headers.get("Retry-After"))
                request_gate.defer(seconds)
                raise RateLimited(seconds)
            response.raise_for_status()
            if not 200 <= response.status_code < 300:
                raise ProviderError(
                    "TVmaze returned an unexpected response. Try again later."
                )
            payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Expected search results")
        return [parse_show(match["show"]) for match in payload]
    except requests.Timeout:
        raise
    except requests.ConnectionError:
        raise ProviderError("Could not connect to TVmaze. Try again later.") from None
    except requests.exceptions.JSONDecodeError:
        raise ProviderError("TVmaze returned invalid data. Try again later.") from None
    except requests.RequestException:
        raise ProviderError("TVmaze is unavailable. Try again later.") from None
    except ValueError, TypeError, KeyError, OverflowError:
        raise ProviderError("TVmaze returned invalid data. Try again later.") from None

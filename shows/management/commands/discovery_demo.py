"""Local-only browser fixtures; never changes the application's provider URL."""

from unittest.mock import MagicMock, patch

import requests
from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command


class Command(BaseCommand):
    help = "Run a loopback-only development server with deterministic TVmaze responses."

    def add_arguments(self, parser):
        parser.add_argument(
            "scenario",
            choices=[
                "timeout",
                "rate-limit",
                "malformed",
                "no-results",
                "missing-data",
                "library",
                "invalid-detail",
            ],
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Discovery fixtures require DEBUG=True.")
        scenario = options["scenario"]
        response = MagicMock(status_code=200, headers={})
        response.__enter__.return_value = response
        response.json.return_value = []
        if scenario == "rate-limit":
            response.status_code = 429
            response.headers = {"Retry-After": "5"}
        elif scenario == "malformed":
            response.json.return_value = {"unexpected": "shape"}
        elif scenario == "missing-data":
            response.json.return_value = [
                {
                    "show": {
                        "id": 1,
                        "name": "Missing metadata example",
                        "url": "https://www.tvmaze.com/shows/1",
                    }
                },
                {
                    "show": {
                        "id": 2,
                        "name": "Broken poster example",
                        "url": "https://www.tvmaze.com/shows/2",
                        "summary": "<p>Plain text &amp; an unavailable poster.</p>",
                        "image": {"medium": "http://127.0.0.1:8000/missing-poster.jpg"},
                    }
                },
            ]
        self.stdout.write(
            f"Demo: {scenario}. No live TVmaze requests. Stop with Ctrl+C."
        )
        fixtures = response.json.return_value
        if scenario in {"library", "invalid-detail"}:
            fixtures = [
                {
                    "show": {
                        "id": 910000000 + number,
                        "name": f"Demo show {number:02d}",
                        "url": f"https://www.tvmaze.com/shows/{910000000 + number}",
                        "summary": (
                            "<p>Local browser fixture &amp; plain-text snapshot.</p>"
                        ),
                        "image": {"medium": "http://127.0.0.1:8000/missing-poster.jpg"},
                    }
                }
                for number in range(1, 22)
            ]

        def fixture_response(url, **kwargs):
            if scenario == "timeout":
                raise requests.Timeout()
            if scenario in {"library", "invalid-detail", "missing-data"}:
                if "/search/shows" in url:
                    response.json.return_value = fixtures
                elif scenario == "invalid-detail":
                    response.json.return_value = {"unexpected": "shape"}
                else:
                    show_id = int(url.rsplit("/", 1)[-1])
                    response.json.return_value = next(
                        (
                            item["show"]
                            for item in fixtures
                            if item["show"]["id"] == show_id
                        ),
                        {},
                    )
            return response

        with patch(
            "shows.tvmaze.requests.get",
            side_effect=fixture_response,
        ):
            call_command("runserver", "127.0.0.1:8000", use_reloader=False)

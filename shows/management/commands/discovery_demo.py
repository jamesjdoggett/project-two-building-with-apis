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
        with patch(
            "shows.tvmaze.requests.get",
            return_value=response,
            side_effect=requests.Timeout() if scenario == "timeout" else None,
        ):
            call_command("runserver", "127.0.0.1:8000", use_reloader=False)

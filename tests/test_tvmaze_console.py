"""Offline checks for error cases that are unreliable to trigger on a live API."""

import argparse
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import MagicMock, patch

import requests

from scripts import test_tvmaze_api as console


class ConsoleTests(unittest.TestCase):
    def run_console(self, phrase="Firefly", payload=None, error=None, json_error=None):
        response = MagicMock()
        response.__enter__.return_value = response
        response.json.return_value = payload
        response.json.side_effect = json_error
        output, errors = io.StringIO(), io.StringIO()
        with (
            patch("sys.argv", ["test_tvmaze_api.py"]),
            patch("builtins.input", return_value=phrase),
            patch.object(
                console.requests, "get", return_value=response, side_effect=error
            ) as get,
            redirect_stdout(output),
            redirect_stderr(errors),
        ):
            status = console.main()
        return status, output.getvalue(), errors.getvalue(), get

    def test_empty_input_does_not_send_request(self):
        status, _, errors, get = self.run_console(phrase="   ")
        self.assertEqual(status, 1)
        self.assertIn("cannot be empty", errors)
        get.assert_not_called()

    def test_success_limits_results_and_handles_missing_metadata(self):
        payload = [{"show": {"name": f"Show {i}"}} for i in range(7)]
        payload[0]["show"]["summary"] = "<p>Hello <b>world</b> &amp; friends.</p>"
        status, output, errors, get = self.run_console(payload=payload)
        self.assertEqual(status, 0)
        self.assertEqual(errors, "")
        self.assertIn("Found 7 matches; showing 5", output)
        self.assertIn("Hello world & friends.", output)
        self.assertIn("Premiered: Unknown", output)
        self.assertIn("Genres: Not listed", output)
        self.assertIn("No summary available.", output)
        self.assertNotIn("Show 5", output)
        self.assertEqual(get.call_args.kwargs["params"], {"q": "Firefly"})
        self.assertEqual(get.call_args.kwargs["timeout"], 10.0)

    def test_no_results_is_success(self):
        status, output, _, _ = self.run_console(payload=[])
        self.assertEqual(status, 0)
        self.assertIn("No shows found", output)

    def test_network_and_http_errors(self):
        response = MagicMock(status_code=503)
        cases = [
            (requests.Timeout(), "timed out"),
            (requests.ConnectionError(), "Could not connect"),
            (requests.HTTPError(response=response), "HTTP error 503"),
            (requests.exceptions.InvalidSchema(), "request failed"),
        ]
        for error, message in cases:
            with self.subTest(error=type(error).__name__):
                status, _, errors, _ = self.run_console(error=error)
                self.assertEqual(status, 1)
                self.assertIn(message, errors)

    def test_non_json_response(self):
        error = requests.exceptions.JSONDecodeError("Invalid JSON", "x", 0)
        status, _, errors, _ = self.run_console(json_error=error)
        self.assertEqual(status, 1)
        self.assertIn("Invalid response", errors)

    def test_invalid_response_shapes(self):
        cases = [
            {},
            [None],
            [{"show": {"name": 42}}],
            [{"show": {"name": "Show", "genres": "Drama"}}],
            [{"show": {"name": "Show", "summary": []}}],
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                status, _, errors, _ = self.run_console(payload=payload)
                self.assertEqual(status, 1)
                self.assertIn("Invalid response", errors)

    def test_timeout_rejects_nonpositive_and_nonfinite_values(self):
        for value in ("0", "-1", "nan", "inf"):
            with (
                self.subTest(value=value),
                self.assertRaises(argparse.ArgumentTypeError),
            ):
                console.positive_timeout(value)


if __name__ == "__main__":
    unittest.main()

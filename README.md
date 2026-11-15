# project-two-building-with-apis

The first API experiment is a standalone console search of TVmaze. It uses Python
3.14 (the installed version used for this project), uv, requests, and Ruff. Django
and Django REST Framework have not been implemented or installed yet.

From the repository root in PowerShell:

```powershell
uv sync --locked
uv run scripts/test_tvmaze_api.py
```

Enter a TV show title when prompted. The script reports the total number of
matches returned and displays the first five in TVmaze's relevance order. Each
includes its title, premiere date, genres, and a wrapped plain-text summary.
Missing optional metadata gets a readable placeholder. No API key is needed.

The agreed choices are one search per run, a default 10-second timeout, and
optional `--url` and `--timeout` arguments for demonstrations. Exit status is `0`
for a valid response (including no results), `1` for empty input or request/response
failure, and `2` for invalid command-line arguments. No automatic retry is made.

## Request-response flow

1. `main()` reads the phrase using `input()`, strips surrounding whitespace, and
   rejects an empty phrase before making any request.
2. `search_shows()` sends an HTTP GET to
   `https://api.tvmaze.com/search/shows`, passing the phrase as the `q` query
   parameter. `requests` performs URL encoding, so spaces and special characters
   do not require hand-built URL strings. An identifying User-Agent is included.
3. TVmaze returns an HTTP status and response body. `raise_for_status()` checks
   for HTTP errors; `response.json()` converts the JSON body to Python lists and
   dictionaries. The response is closed after it is read.
4. The script checks that the response is a list containing valid `show` objects
   and that the fields it displays have usable types. Invalid JSON or an
   unexpected response structure produces a useful message instead of a traceback.
5. `display_shows()` prints up to five shows. `SummaryParser` removes HTML tags
   and decodes entities; `textwrap` wraps summaries for console reading. Output
   uses UTF-8 so international names also work when output is piped on Windows.

Timeouts, connection failures, HTTP failures, and invalid responses have separate
messages. The timeout applies to connection/read waits, not a strict deadline for
the entire process. Personal notes, authentication, saving, and database access
belong to the future Django project.

## Demonstration commands

These PowerShell commands pipe user input into the same prompt used interactively:

```powershell
# Successful real search: prints matching shows, exit 0.
'Firefly' | uv run scripts/test_tvmaze_api.py

# Empty/whitespace search: no request sent, exit 1.
'   ' | uv run scripts/test_tvmaze_api.py

# No matching shows: normal response, exit 0.
'zzzzprojecttwonomatchqwerty987654321' | uv run scripts/test_tvmaze_api.py

# Connection failure: assumes nothing is listening locally on port 1, exit 1.
'Firefly' | uv run scripts/test_tvmaze_api.py --url http://127.0.0.1:1 --timeout 5

# HTTP 404: official host, nonexistent endpoint, exit 1.
'Firefly' | uv run scripts/test_tvmaze_api.py --url https://api.tvmaze.com/project-two-not-an-endpoint

# Valid JSON with the wrong shape (a show object, not search results), exit 1.
'Firefly' | uv run scripts/test_tvmaze_api.py --url https://api.tvmaze.com/shows/1

# Very short timeout: usually times out, but network behavior can vary, exit 1.
'Firefly' | uv run scripts/test_tvmaze_api.py --timeout 0.000001

# Run immediately after a command to inspect its exit status.
$LASTEXITCODE
```

The successful search, no-results case, 404, wrong JSON shape, refused connection,
and short-timeout case were exercised during development. Network-dependent
commands can produce a different failure if connectivity is unavailable. Offline
checks cover timeouts, connection errors, HTTP errors, malformed JSON, wrong
response shapes, missing metadata, empty input, and the five-result limit:

```powershell
uv run python -m unittest discover -s tests -v
uv run ruff check .
uv run ruff format --check .
```

TVmaze documents fuzzy name search and its response format in its
[official API documentation](https://www.tvmaze.com/api). Data is attributed to
TVmaze under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/);
displayed summaries are converted to plain text. See the
[provider comparison](research/api-provider-comparison.md) for selection research.

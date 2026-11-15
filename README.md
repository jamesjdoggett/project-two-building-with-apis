# project-two-building-with-apis

ShowVault Phase 1 provides administrator-created ordinary accounts, session
sign-in/sign-out, a protected welcome page, and TVmaze discovery. Saving shows,
personal libraries, HTMX results, and REST endpoints belong to later phases.
Phase 1 is awaiting manual review; nothing has been committed by this session.

## Run the Phase 1 website

From the repository root in PowerShell, using the existing uv environment:

```powershell
uv sync --locked
uv run python manage.py migrate
uv run python -X utf8 manage.py tailwind build
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Create a superuser only if you do not already have one. Open
<http://127.0.0.1:8000/admin/>, sign in as that administrator, and add two users
under Authentication and Authorization → Users. Give each a usable password;
leave Staff status and Superuser status unchecked and Active checked. Sign out
of admin, then use <http://127.0.0.1:8000/accounts/login/> for ordinary sign-in.
Passwords are chosen locally; no demo accounts or fixed credentials are seeded.

### Browser verification

1. While signed out, visit `/` and `/discover/`. Both should redirect to sign-in.
   Try incorrect credentials: an accessible error appears and you remain signed
   out. Sign in with either ordinary account: its welcome page and discovery are
   available without staff privileges. `/admin/` remains inaccessible to that user.
2. Submit `Firefly` in discovery. Results should show recognizable titles,
   premiere years when known, summaries, and posters. Follow a TVmaze source
   link and inspect the attribution/license/transformation notice. Results retain
   relevance order; the console script's five-result cap does not apply here.
3. Submit whitespace: expect “Enter a show title” without a provider request.
   Submit `zzzzprojecttwonomatchqwerty987654321`: expect a normal no-shows message
   and retained query, with no red failure banner. Wait at least one second
   between searches; earlier requests receive local wait guidance.
4. Test with JavaScript disabled: ordinary GET searches must still work. With
   JavaScript enabled, search submission shows loading feedback. Check keyboard
   navigation, visible focus, labels, narrow-window layout, and the sign-out button.
5. Sign out using the button: discovery requires sign-in again. Navigating to
   `/accounts/logout/` directly must return Method Not Allowed instead of logging
   you out. Sign in with the other ordinary account and repeat the access checks.
6. For deterministic errors and missing metadata, stop the ordinary server with
   Ctrl+C and run one of the commands below. Sign in using the same local
   accounts, submit any nonblank query on `/discover/`, and verify its expected
   state. Stop each fixture server before starting the next.

```powershell
uv run python manage.py discovery_demo timeout
uv run python manage.py discovery_demo rate-limit
uv run python manage.py discovery_demo malformed
uv run python manage.py discovery_demo no-results
uv run python manage.py discovery_demo missing-data
```

The timeout fixture shows retry guidance; rate-limit asks you to wait five seconds;
malformed shows invalid-data feedback. All retain the query and show no traceback.
No-results is a normal empty state. Missing-data returns two fixture cards with
unknown years, missing-summary fallback, plain-text summary conversion, and both
absent and broken posters replaced by the local placeholder. Verify the broken
image fallback with JavaScript enabled. The demo command binds only to
127.0.0.1:8000, requires DEBUG, intercepts only outbound TVmaze requests in that
process, and creates no accounts or saved data. Restart `runserver` to resume real
TVmaze access; there is no public URL or query parameter for selecting fixtures.

### Phase 1 automated checks

```powershell
uv run pytest
uv run python -m unittest discover -s tests -v
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run ruff check .
uv run ruff format --check .
uv run python -X utf8 manage.py tailwind build
```

Tests mock TVmaze, including timeouts, connection failures, 429, other HTTP
failures, invalid JSON/shapes, optional fields, escaping, and shared throttling.
Authentication tests cover admin account creation, non-staff access, CSRF,
POST-only logout, inactive accounts, and safe login redirects. The request gate
allows one outbound request per second across users/threads within one local
server process and extends its cooldown from Retry-After seconds or HTTP dates;
it does not coordinate multiple server processes. No automatic retry is made.

The [implementation plan](plans/showvault.md) and [AGENTS.md](AGENTS.md) describe
the approved scope and project conventions. Provider behavior was checked against
[TVmaze's official documentation](https://www.tvmaze.com/api); session login/logout
uses [Django's built-in authentication views](https://docs.djangoproject.com/en/5.2/topics/auth/default/).
The CSS build follows [django-tailwind-cli's usage documentation](https://django-tailwind-cli.readthedocs.io/latest/usage/).

## Original console API experiment

The first API experiment is a standalone console search of TVmaze. It uses Python
3.14 (the installed version used for this project), uv, requests, and Ruff. It
remains separate from the Django application; DRF endpoints are not implemented.

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

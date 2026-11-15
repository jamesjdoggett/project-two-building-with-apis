# project-two-building-with-apis

ShowVault now supports administrator-created ordinary accounts, session
sign-in/sign-out, TVmaze discovery, authoritative show saving, and private local
libraries. Phase 2 is implemented and awaiting browser review. Personal editing,
refresh/deletion, local search/filter/sort controls, HTMX, and REST endpoints remain
in their approved later phases. This session has made no commits.

## Run the website

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

### Phase 2 browser verification

Use a fresh ordinary account for an initially empty library, a second ordinary
account, and an administrator/staff account. New Phase 2 migrations must be applied
with the setup commands above. Leave at least one second between provider actions;
if you save immediately after searching, wait guidance and an explicit retry button
are expected because search and save share the request budget.

1. While signed out, visit `/library/` and a known `/library/<id>/` URL: both
   redirect to sign-in. Sign in as the fresh ordinary account: the destination is
   `/library/`, showing an empty-library message and discovery link. `/` also
   redirects there. Confirm this user cannot access Django admin.
2. Search `Firefly`, wait a second, and select **Save to library**. You should land
   on `/library/<local-id>/`, showing the authoritative title, plain-text summary,
   genres, language, dates, TVmaze status, poster, source/license/transformation
   notice, successful retrieval time, and saved time. Missing metadata reads
   **Unknown** or uses another clear placeholder. Personal defaults are **Planned**,
   **Unrated**, **No notes yet.**, and **No bookmark set.** There are no edit,
   refresh, delete, or API controls in this phase.
3. Record the detail URL and retrieval time. Open **My library**: its card opens
   that detail page. Search again: only shows saved by this account have a
   **Saved** badge and **Open saved entry** button. Click that button repeatedly:
   the URL, snapshot, retrieval time, and number of library entries remain the
   same. In a separate tab, leave these discovery results open for step 6.
4. Sign in as the second ordinary user in a separate browser profile/private
   window. Its library starts empty and the first user's detail URL returns 404.
   Save the same show: it receives a different local detail URL and its own
   retrieval time. The first entry remains unchanged. Sign in as staff/admin on
   the ordinary website: the first user's URL must still return 404, and the
   staff account's library contains only its own entries.
5. For repeatable fixture tests, stop `runserver` and run
   `uv run python manage.py discovery_demo library`. It serves 21 synthetic shows
   for any nonblank search and matching authoritative fixture detail responses,
   without live HTTP. Use another fresh ordinary account and search `demo`.
   Save all 21 cards (go back to the results after each save, waiting a second
   between requests). Its library must contain exactly 20 entries on page 1 and
   one on page 2, newest saved first, with working **Next**/**Previous** links.
   `/library/?page=bad` uses page 1; `?page=999` uses the last page. These fixture
   entries persist in the selected user's local library; use a dedicated test
   account to keep them separate from real shows. The deliberately broken posters
   should become local placeholders with JavaScript enabled. Inspect detail
   placeholders, provenance, and personal defaults as well.
6. Keep one discovery results tab showing a saved card and an unsaved card.
   Stop the fixture/normal server and start
   `uv run python manage.py discovery_demo timeout`. Without reloading that
   results tab, submit the saved card's **Open saved entry**/**Save to library**
   button: it still opens the original local entry with unchanged retrieval time.
   Submit the unsaved card: expect a timeout message, no new entry, and an explicit
   retry button. Directly reload the saved detail and library URLs: text and
   provenance remain available. Browser DevTools offline mode would also block
   localhost, so use this server fixture to simulate a provider outage.
7. Stop that server and run
   `uv run python manage.py discovery_demo invalid-detail`. Search `demo` and save
   a synthetic show not yet saved by the signed-in account. Expect an invalid-data
   error with no traceback and no new library entry. If all 21 are already saved,
   use a different ordinary account: repeat saves intentionally bypass invalid
   provider responses. The fixture exposes valid discovery results and invalid
   detail responses, so it tests the save boundary specifically.
8. Retest ordinary discovery, blank/no-results searches, sign-out, keyboard
   navigation, narrow layouts, and saving with JavaScript disabled. Text is escaped
   and saving works through ordinary protected POST forms. Visiting
   `/discover/180/save/` in the address bar returns 405 and never saves. Sign out
   using the button; the library and details require sign-in again. Stop fixture
   servers and restart `uv run python manage.py runserver` to restore live TVmaze.

The existing `timeout`, `rate-limit`, `malformed`, `no-results`, and `missing-data`
discovery fixtures remain available. To test save-time 429 or malformed failures,
keep an unsaved card open before restarting with the corresponding fixture, then
submit that existing card. Rate limiting reports the wait interval; failed saves
create no partial entry. All fixture servers require DEBUG and bind to loopback;
there is no public failure-selection parameter. SQLite competing saves may return
a safe **library is busy** retry page when a winning row is not yet visible.

Phase 2 stores only snapshot/provenance fields. The displayed personal defaults
are fixed until Phase 3 introduces their persisted fields and editing. Unique
owner/show and positive provider-ID constraints are database-enforced. The shared
save operation checks for an owned duplicate before HTTP, recovers unique insert
collisions, and handles SQLite lock contention without retrying provider requests.

### Phase 2 automated verification

Actual results from this session:

- `uv run pytest`: **162 passed**, including 13 console subtests. One pytest
  cache-write warning reported Windows error 183 for `.pytest_cache/v/cache`;
  test execution and assertions passed.
- `uv run python -m unittest discover -s tests -v`: **7 passed**.
- `uv run python manage.py check`: no issues.
- `uv run python manage.py makemigrations --check --dry-run`: no changes detected.
- `uv run python manage.py migrate`: `shows.0001_initial` applied successfully.
- `uv run ruff check .`: all checks passed.
- `uv run ruff format --check .`: all 45 Python files formatted.
- `uv run python -X utf8 manage.py tailwind build`: production stylesheet built.

Both selected TDD behaviors were observed failing on assertions before their
implementation, then passing: authoritative owned saving and unchanged/no-HTTP
repeat saving. Additional coverage includes provider detail failures and ID
mismatches, forged inputs, database constraints, unique-collision recovery, SQLite
lock feedback, two genuinely competing saves on separate database connections,
staff/superuser privacy, local rendering with HTTP forbidden, and 20/1 pagination.
The concurrency test coordinates both initial misses before inserts and allows
SQLite's explicit safe-retry outcome; a sequential duplicate is not counted as
concurrency evidence.

Browser scenarios above remain for user review; this record does not claim that
browser layout or interactive poster fallback was manually verified. No Phase 3
features, commits, or pushes were performed.

### Phase 1 discovery regression scenarios

1. While signed out, visit `/` and `/discover/`. Both should redirect to sign-in.
   Try incorrect credentials: an accessible error appears and you remain signed
   out. Sign in with either ordinary account: its library and discovery are
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

### Automated checks

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

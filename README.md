# project-two-building-with-apis

ShowVault now supports administrator-created ordinary accounts, session
sign-in/sign-out, TVmaze discovery, authoritative show saving, and private local
libraries, personal editing, local search/filter/sort controls, explicit metadata
refresh, confirmed deletion, and HTMX discovery/library interactions. Phase 4 is
implemented and awaiting browser review. REST endpoints remain in Phases 5–6.
This session has made no commits.

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

### Phase 4 browser verification

Use two ordinary accounts and a staff account in separate browser profiles. Stop
the running development server before switching demo scenarios. Every demo server
uses `127.0.0.1:8000`, requires DEBUG, and mocks server-side provider HTTP only.
Wait at least one second between discovery, save, and refresh, or follow the
displayed cooldown; they deliberately share one throttle.

1. Run `uv run python manage.py discovery_demo library`. Search `demo`, save a
   show in each ordinary account, and give the first copy notes, a rating,
   Completed status, and S0 E1. Record its title and successful retrieval time.
   Stop the server and run `uv run python manage.py discovery_demo refreshed`.
   On the first account's detail, choose **Refresh TVmaze metadata**. Expect the
   title to gain `refreshed`, the summary to become **Updated provider snapshot.**,
   and a newer retrieval time. Personal values and saved time stay unchanged;
   the second account's snapshot stays unchanged.
2. Stop/restart with each scenario: `timeout`, `rate-limit`, `removed`, and
   `malformed`. Refresh the saved entry each time. Expect retry guidance (and
   wait guidance for rate limiting), while all saved metadata, successful
   retrieval time, and personal values remain unchanged. Under `timeout`, library
   queries, detail, personal edits, and deletion must still work.
3. Click **Delete entry**. Expect a confirmation naming the show and explaining
   permanent loss of notes, rating, status, and bookmark. Click **Cancel** and
   verify nothing changed. Reopen and choose **Permanently delete**: expect the
   library, success feedback, and no entry. Restart the `library` fixture, search,
   and save that show again: expect Planned, Unrated, blank notes, no bookmark.
   Discovery's Saved indicator must disappear after deletion and return on save.
4. With `library` running, search/save up to 21 demo shows. In My library combine
   a title query, Planned status, and each sort; use Next/Previous. Expect 20
   entries then one, retained controls, and a URL matching the current page.
   Requests update only the controls/results panel. Test Back/Forward, Reset,
   no matches, and a fresh account's empty library. Discovery retains its query
   after errors. In DevTools Network, throttle the connection to see loading
   feedback (the deterministic timeout fixture fails immediately). Block
   `/discover/?*` in DevTools to check request-failure feedback and retry.
5. Disable JavaScript and repeat discovery, local filtering/pagination, refresh,
   and cancel/confirm deletion. Expect usable conventional pages and forms.
   Re-enable JavaScript. Leave a library/discovery tab open, sign out in another
   tab, then submit its controls: expect full navigation to login, with the
   attempted URL retained in `next`, rather than login inside the results.
6. As the second account and staff on ordinary website routes, try the first
   account's `/library/<id>/delete/` and POST refresh/delete URLs: expect 404 and
   no change. GET `/library/<owned-id>/refresh/` must return 405. For CSRF, use
   DevTools `fetch('/library/<owned-id>/refresh/', {method: 'POST'})`: expect 403;
   repeat with the delete URL. Normal form submissions succeed with their token.

HTMX 2.0.8 and its Zero-Clause BSD license are stored in `static/shows/`; no CDN
is needed. Shared fragments include controls, results, loading, and feedback.
Browser history caching is disabled so private fragments are not stored in
HTMX's localStorage history cache. Provider summaries and notes remain escaped,
and swapped posters use the same local failure placeholder as initial pages.
Browser verification remains pending; automated tests do not establish visual
layout, keyboard behavior, or actual browser navigation.

### Phase 4 automated verification

The three selected TDD behaviors reached assertion failures before passing:
preserving an edit during refresh HTTP, returning 404 after deletion during
refresh HTTP without resurrection, and full login navigation for expired HTMX
sessions. Other tests cover complete failure preservation, independent snapshots,
optional metadata, shared throttling, CSRF, methods, forged payloads, ordinary and
staff ownership, confirmed deletion/re-save defaults, fragment parity, normalized
controls, pagination, empty states, saved indicators, and discovery failures.

Actual final results:

- `uv run pytest`: **286 passed**, including **60 new Phase 4 tests**.
- `uv run python -m unittest discover -s tests -v`: **7 passed**.
- `uv run ruff check .`: passed; `uv run ruff format --check .`: **56 files** formatted.
- `uv run python manage.py check`: no issues.
- `uv run python manage.py makemigrations --check --dry-run`: no changes detected.
- `uv run python manage.py migrate --check`: passed; no unapplied migrations.
- `uv run python -X utf8 manage.py tailwind build`: production stylesheet built.
- `git diff --check`: passed.

Checks used a workspace-local `UV_CACHE_DIR` because the sandbox denied access
to the default uv cache; the CSS executable required execution outside the sandbox.
No model change or new migration is needed. Manual review remains pending;
Phase 5 has not started. No commit or push was made.

### Phase 3 browser verification

The Phase 3 migrations have been applied locally. For another checkout, run the
setup commands above before testing. Use two ordinary accounts and a staff/admin
account, with separate browser profiles for isolation checks.

1. Sign in, open a saved show's detail, and click **Edit viewing details**.
   Existing snapshots start with Planned, Unrated, blank notes, and no bookmark.
   The form must show saved values when reopened. Change a value and click
   **Cancel**: the detail must remain unchanged. Loading an edit URL never saves.
2. Save a rating of `1`, then `10`, then blank. Expect the chosen value on detail
   and the library card; blank displays **Unrated**. Enter two note lines including
   `<script>alert("test")</script>`: they display as literal text with line breaks,
   and no script executes. Reopen the form and verify the text is preserved.
   Blank notes are valid and display **No notes yet.**
3. Test the notes boundary precisely: on the edit page, open DevTools Console and
   run `document.querySelector('[name="notes"]').value = 'n'.repeat(5000)`, then
   save. All 5,000 characters must persist. For server-side rejection testing,
   in DevTools Elements add `novalidate` to the edit `<form>` and remove
   `maxlength` from the notes textarea, then set its value to `'n'.repeat(5001)`
   and submit. Expect **Nothing was saved** and a notes error. Reopen detail in a
   separate tab: the last valid notes and all other values must be unchanged.
4. With browser validation disabled on that form as above, submit rating `0`,
   `11`, and `1.5` separately; season `-1` and `1.5`; episode `0` and `1.5`;
   and each partially filled bookmark pair. Each must return a field error,
   retain the attempted form values for correction, and leave all saved values
   unchanged. For any test, also change a valid field such as notes before
   submitting, then check that it was not partially saved. Normal browser
   validation may prevent these submissions before reaching Django.
5. Save **S0 E1** and choose each of Planned, Watching, Paused, Completed, and
   Dropped in turn. The status must change only when chosen; the bookmark stays
   S0 E1. In Completed, save S3 E8 and correct it to S3 E7: status stays Completed.
   Choose Paused and correct to S2 E4: status stays Paused. Choose Completed,
   then Planned to plan a rewatch: S2 E4 stays. Check **Clear bookmark (keep watch
   status)** and save: the bookmark becomes **No bookmark set.**, status stays
   Planned. Reopen: both number fields are blank and Clear bookmark is unchecked.
   Entering and saving two blank number fields also explicitly removes a bookmark.
6. For repeatable pagination, use a dedicated fresh ordinary account and start
   `uv run python manage.py discovery_demo library` after stopping any other
   development server. Search `demo` and save its 21 fixture shows, waiting at
   least one second between provider actions. All start Planned. Give two shows
   rating 10, another rating 1, and leave the rest Unrated. Keep every show's
   status Planned for the next combined-filter pagination check.
7. In **My library**, submit title `  dEmO sHoW  `, status **Planned**, and sort
   **Personal rating (highest first)**. Expect 21 matches, with rating 10 first,
   then 1, then Unrated. Page 1 has 20 entries; **Next** opens the remaining one.
   The trimmed title, selected status, and sort must persist in controls and URLs
   through Next/Previous. Refresh the same URL: tied ratings retain their order.
   Try **Title A–Z** and **Recently saved**, and filter each status after editing
   one show to it. **Apply** starts at page 1; **Reset** clears the controls.
8. Check `/library/?q=demo&status=planned&sort=rating&page=bad`: first page.
   Use `page=999`, `page=0`, or `page=-1`: last page. Use
   `/library/?status=invalid&sort=invalid`: All statuses and Recently saved.
   Search a nonexistent local title: **No saved shows match these filters**
   with a reset link. A separate account with no saved entries instead sees
   **Your library is empty**, even if another account has matching shows.
9. Stop the fixture server and run
   `uv run python manage.py discovery_demo timeout`. Directly open saved detail,
   edit and save personal fields, and repeat all library controls and pagination.
   These local operations must still succeed; discovery must report a timeout.
   Successful edits never change the metadata snapshot or retrieval time.
   An already-open saved discovery card still opens the same entry unchanged.
   Use this server fixture rather than browser offline mode, which blocks localhost.
10. As the second ordinary account and then staff/admin on the ordinary website,
    request the first account's `/library/<id>/edit/`: expect 404. Their libraries
    and filtered counts contain only their own shows. Sign out and request an
    edit URL: expect login. Disable JavaScript and check that editing, error
    feedback, library controls, and pagination still work as conventional forms.
11. For a forged-field check while signed in on your own edit page, run the
    following in DevTools Console (the form's CSRF token is included):

    ```javascript
    const editForm = document.querySelector('[name="rating"]').form;
    const forged = new FormData(editForm);
    forged.set('owner', '999999');
    fetch(editForm.action, {method: 'POST', body: forged}).then(r => console.log(r.status));
    ```

    Expect `400` and no saved changes. Repeat with `forged.delete('owner')` and
    `forged.set('title', 'Forged title')`: also 400. To check CSRF, delete both
    forged fields and `csrfmiddlewaretoken` from this FormData and submit again:
    expect 403. Reload detail to verify unchanged data. These are temporary
    browser requests, not changes to application code.

Stop the fixture server and use `uv run python manage.py runserver` to restore
live TVmaze. Check keyboard focus, visible errors, and narrow-window layout.
Refresh, deletion, HTMX, and REST endpoints are intentionally deferred.

### Phase 3 automated verification

Actual results from this implementation session:

- `uv run pytest`: **226 passed**, including 64 new Phase 3 tests. One existing
  pytest cache-write warning reported Windows error 183 for `.pytest_cache/v/cache`;
  no test failed.
- `uv run python -m unittest discover -s tests -v`: **7 passed**.
- `uv run python manage.py check`: no issues.
- `uv run python manage.py makemigrations --check --dry-run`: no changes detected.
- `uv run python manage.py migrate`: `shows.0002` personal fields and
  `shows.0003` constraints applied successfully.
- `uv run ruff check .`: all checks passed.
- `uv run ruff format --check .`: all **52** Python files formatted.
- `uv run python -X utf8 manage.py tailwind build`: production stylesheet built.

Each selected TDD test failed on an assertion before its implementation and passed
afterward: invalid-edit preservation, visible independent bookmark corrections/
rewatch/clear, and combined private query controls with retained pagination.
Additional tests cover all five statuses, validation boundaries and parsed types,
escaping, provider/snapshot immutability, database numeric/status/pair constraints,
existing-row migration defaults, forbidden fields, ownership including staff and
superusers, session CSRF, normalized choices, deterministic sorts, malformed pages,
distinct empty states, and local operations with HTTP forbidden.

Browser verification above remains for user review; automated results do not claim
manual browser acceptance. No Phase 4 implementation, commits, or pushes were made.

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
   **Unrated**, **No notes yet.**, and **No bookmark set.** Phase 3 now adds editing;
   refresh, delete, and API controls remain deferred.
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

Phase 2 originally stored only snapshot/provenance fields; Phase 3 now persists
the personal fields and exposes editing. Unique
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

## Phase 5 private REST API

Actual final verification: **387 pytest tests and 13 subtests passed**, including
101 Phase 5 API tests. One existing Windows pytest-cache write warning remains.
The separate seven-method console suite passed. Ruff lint and formatting
(59 files), Django system checks, migration consistency and applied-migration
checks, `uv sync --locked`, production CSS build, and diff whitespace checks
passed. No new migration is required. Browser review is pending; no commit or
Phase 6 implementation was made.

The API uses the same entries as the website. Sign in at `/accounts/login/`,
then open `/api/entries/` for DRF's browsable API. JSON clients send
`Accept: application/json` and `Content-Type: application/json`. Retain the
`sessionid` and `csrftoken` cookies; every POST/PUT/PATCH also requires
`X-CSRFToken` containing the current CSRF cookie value (login rotates it).
There are no API tokens or public signup. Anonymous requests receive structured
403 errors; another owner's ID and a missing ID both return 404, including staff.

| Request | Input / result |
| --- | --- |
| `GET /api/entries/` | Owned entries, 20 per page |
| `GET /api/entries/<id>/` | Owned local snapshot, personal values and provenance |
| `POST /api/entries/` | Only `{"tvmaze_id":180}`; 201 new, 200 unchanged duplicate |
| `PUT /api/entries/<id>/` | All five personal fields required; replaces personal state only |
| `PATCH /api/entries/<id>/` | Supplied personal fields only; validates merged resulting state |

Lists accept `q` (trimmed case-insensitive title substring), `status` (`planned`,
`watching`, `paused`, `completed`, `dropped`), `sort` (`recent`, `title`, `rating`),
and `page`. Invalid status/sort normalize to no filter/recent; malformed pages
select page 1 and out-of-range pages select the last page, matching the website.
`rating` sorts highest first, Unrated last. Ties are deterministic. Responses
contain `count`, `page`, `pages`, `next`, `previous`, normalized `q/status/sort`,
and `results`; next/previous are page numbers or null. Retain the query controls
when requesting another page. Empty lists have count 0, pages 1, and results [].

A complete PUT body (use the browsable API's raw JSON input) is:

```json
{"rating":8,"notes":"Private notes\nSecond line","watch_status":"completed","last_season":0,"last_episode":1}
```

Rating accepts integer 1–10 or null. Notes are a string of at most 5,000
characters (empty allowed, whitespace/line breaks preserved). Season is an integer
>=0 and episode an integer >=1, both at most 9223372036854775807; both may be
null. JSON booleans, numeric strings and floating-point numbers are not integers.
PATCH may correct one bookmark value if the existing other value completes the
pair; clear with `{"last_season":null,"last_episode":null}`. Changing status
never changes bookmarks, and bookmark edits never change status. Ownership,
metadata, provenance, IDs and timestamps cannot be supplied on update; create
rejects everything except tvmaze_id. Invalid writes return field-keyed 400 errors
and preserve the entry. Representations exclude account/owner information.

New saves use authoritative TVmaze data and Planned/Unrated/blank defaults.
Duplicates bypass HTTP and preserve every value and timestamp. Provider timeout
returns 504; rate limits return 503 with integer `retry_after` and `Retry-After`;
provider missing show on creation returns 400 on `tvmaze_id`; other upstream,
connection, malformed-data and ID-mismatch failures return 502. SQLite save
contention returns retryable 503 with wait guidance. Provider failures have a
safe `detail` message and never create partial records. Local reads/edits work
without TVmaze. API refresh and DELETE belong to Phase 6 and are unavailable.

Manual Phase 5 review (browser verification remains pending):

1. Run migrations, `uv run python -X utf8 manage.py tailwind build`, then
   `uv run python manage.py runserver`. Sign in and open `/api/entries/`.
   Check JSON/browsable results and provenance. Combine filters/sorts and page
   through 21+ entries; expect 20 on page 1 and retained normalized controls.
2. POST a new ID as raw JSON with session CSRF; expect 201. Repeat the same ID
   while the controlled timeout fixture is active; expect 200 with identical
   data. Existing `discovery_demo` fixtures can simulate upstream failures;
   see the earlier fixture instructions. A new ID timeout returns 504 and
   creates nothing. Owner/metadata overrides and invalid IDs return 400.
3. PATCH rating/notes/status, then PUT all five personal fields with the example
   above. Reload `/library/<id>/` and its edit form; expect the same values and
   escaped notes. Try a one-null bookmark (400), then both null (200). Try
   incomplete PUT (400). Status and bookmark must remain independent.
4. Sign in as a second user and as staff; the first user's ID returns 404 for
   GET/PUT/PATCH and does not appear in lists. Sign out; expect API JSON 403.
   Omit X-CSRFToken on an authenticated JSON mutation; expect 403 and no change.

For JSON writes from the browser developer console on a signed-in local page:

```javascript
const csrf = document.cookie.split('; ').find(c => c.startsWith('csrftoken=')).split('=')[1];
await fetch('/api/entries/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
  body: JSON.stringify({tvmaze_id: 180})
}).then(async r => ({status: r.status, body: await r.json()}));
```

Use the same headers with PATCH/PUT and an entry URL. Cookies are included on
same-origin fetches. Re-read the CSRF cookie after signing in again.

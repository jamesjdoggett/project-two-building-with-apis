# PROMPTS.md — AI Usage Log

## 2026-11-14 — TVmaze interview, uv setup, and console API verification

### Prompts

1. "$grill-me  I have selected TVmaze as the external API provider for Project #2. Interview me about any important decisions before implementing a standalone Python console script named scripts/test_tvmaze_api.py. This is a future Django and Django REST Framework project, so initialize the Python environment using uv, not pip or another package manager. The script must accept a TV show search phrase from user input, send a real HTTP request to the official TVmaze API, and display matching show titles, premiere dates, genres, and summaries in a readable format. Handle empty searches, no results, timeouts, connection failures, HTTP errors, and invalid responses with useful messages. Keep the code simple enough to explain during a design defense. Do not build the Django application yet. After implementation, explain the request-response flow and provide commands to test successful, empty, and failed requests."
   The attached `grill-me` skill instructed the agent to explore the codebase first, ask one beginner-friendly question at a time, explain options and tradeoffs, and recommend an option.
2. "go with the recommended options" — accepted `requests`, installed through uv.
3. "recommended option" — accepted displaying the first five matches and reporting the total returned.
4. "recommended option" — accepted optional `--url` and `--timeout` arguments for failure demonstrations.
5. "recommended option" — accepted one search per run; empty input/errors exit nonzero, while no matches is a successful response.
6. "Update PROMPTS.md with our actual Project #2 research and API verification sessions. Record the prompts used, providers compared, primary-source references, final provider choice and justification, script implementation, and actual test results. Do not invent prompts, outcomes, or successful tests. Keep existing entries."

### Provider choice and implementation

- The user selected **TVmaze** after the research recommended it as easiest. The justification was public search without API credentials, fuzzy title search, useful show metadata and stable identifiers, and a small search-to-display workflow suitable for a classroom defense. Attribution and ShareAlike obligations still apply.
- The agent revisited the [official TVmaze API documentation](https://www.tvmaze.com/api) for `/search/shows?q=...`, response structure, and usage rules. The report and README link the [CC BY-SA 4.0 license](https://creativecommons.org/licenses/by-sa/4.0/).
- Initialized the project using `uv init --bare --python 3.14`, then `uv add requests` and `uv add --dev ruff`. Created `.venv`, `pyproject.toml`, `uv.lock`, and a `.python-version` selecting 3.14. The installed interpreter reported Python 3.14.7. No pip was used.
- Implemented `scripts/test_tvmaze_api.py`: prompt and trim input; reject blanks before networking; GET the official search endpoint with `params={"q": phrase}`, a User-Agent and default 10-second timeout; check HTTP status; decode and validate JSON; print up to five titles, premiere dates, genres and summaries with missing-field placeholders. HTML summaries become wrapped plain text. UTF-8 output supports international text on Windows.
- Added separate messages for timeouts, connection failures, HTTP errors, invalid JSON and invalid response shapes. Added positive/finite timeout validation and optional URL override. Added TVmaze attribution and a license link.
- Added `tests/test_tvmaze_console.py` with offline checks and documented setup, request-response flow, exit statuses, and PowerShell demonstrations in `README.md`. Django, DRF, authentication, database persistence and saved-item features were not implemented.

### Actual verification results

The following are observed results from this session, not promises about future network behavior. Piped strings were supplied to the script's normal `input()` prompt.

| Check / command | Observed result |
| --- | --- |
| `'Firefly' \| uv run scripts/test_tvmaze_api.py` after the encoding fix | Exit 0; reported five matches and displayed titles, dates, genres and summaries, including international text. |
| `'   ' \| uv run scripts/test_tvmaze_api.py` | Exit 1; useful empty-search message. The offline test also verified no request was sent. |
| `'zzzzprojecttwonomatchqwerty987654321' \| uv run scripts/test_tvmaze_api.py` | Exit 0; no-shows-found message. |
| `'Firefly' \| uv run scripts/test_tvmaze_api.py --url http://127.0.0.1:1 --timeout 1` | Exit 1; timed out on this Windows environment, rather than immediately reporting a refused connection. |
| Same localhost command with `--timeout 5` | Exit 1; "Could not connect" message. |
| `'Firefly' \| uv run scripts/test_tvmaze_api.py --url https://api.tvmaze.com/project-two-not-an-endpoint` | Exit 1; HTTP 404 message. |
| `'Firefly' \| uv run scripts/test_tvmaze_api.py --url https://api.tvmaze.com/shows/1` | Exit 1; invalid-response message because this endpoint returns a show object rather than a search-result list. |
| `'Firefly' \| uv run scripts/test_tvmaze_api.py --timeout 0.000001` | Exit 1; timeout message. This timing-dependent demonstration is not guaranteed on every network. |
| `uv run python -m unittest discover -s tests -v` | Final run: 7 test methods passed, `OK`, exit 0. Covered blank input, five-result cap, missing metadata, HTML conversion, no results, timeout/connection/HTTP/generic request errors, invalid JSON, invalid shapes and invalid timeout values. |
| `uv run ruff check .` | Final run: "All checks passed!", exit 0. |
| `uv run ruff format --check .` | Final run: "14 files already formatted", exit 0. This was Ruff's reported file count, not a claim that 14 files were added. |
| `git diff --check` | No whitespace errors; Git emitted LF-to-CRLF notices for README.md. |

Malformed JSON and the HTTP 503 case were simulated in offline tests; no live malformed-JSON or live HTTP 503 result was observed. No provider uptime benchmark was run. The log update itself did not rerun the script or tests.

### Summary

- **Outcome:** a uv-managed standalone TVmaze console script, seven passing offline test methods, successful live API verification, and explanatory README commands. Existing research was retained; the Django application remains future work.
- **Deviations:** the user accepted all recommended interview options. The agent continued asking one decision at a time after the general "go with the recommended options" reply. Failure-test URL and timeout arguments were explicitly agreed upon.
- **Sideways:** the shell's `python` alias could not execute; uv found the installed interpreter. Sandbox access initially blocked uv's cache and a live request, so those operations were rerun with escalation. uv fell back from hardlinks to copies while installing dependencies. An initial Ruff check reported two TRY004 findings; exception types were corrected. One patch failed to apply after formatting changed its expected context and was reapplied against the current file. The first offline suite failed because `InvalidSchema` was categorized as an invalid response; exception ordering was corrected and all seven methods then passed. The first elevated live Firefly run printed several shows but exited 1 with `UnicodeEncodeError` under Windows cp1252; explicit UTF-8 output fixed it, and the repeated live run exited 0. A one-second localhost test produced a timeout; five seconds allowed the refused-connection case to be observed. None of these failed attempts is counted as a successful test above.

## 2026-11-14 — Project #2 public API provider research

### Prompts

1. "$research Research free public APIs for Project #2, a Django application using Django REST Framework, SQLite, uv, and Ruff. The application must let authenticated users search an external API, save selected items locally, add personal notes, ratings, or progress, and manage their saved items through both a website and our own REST API. Compare video game, movie, television, music, and book APIs. Use official primary-source documentation to verify authentication requirements, free-tier limits, available endpoints, search capabilities, data fields, licensing restrictions, and reliability. Recommend three practical providers, explain possible application ideas, and identify which would be easiest to develop and demonstrate. Save the findings with source links in research/api-provider-comparison.md. Do not implement the application yet."
   The attached `research` skill required a background agent to investigate primary sources and write a single Markdown findings file with source citations.

### Providers and primary-source references

- **Television — TVmaze:** [official API documentation](https://www.tvmaze.com/api), [official show response](https://api.tvmaze.com/shows/1), and the API-linked [CC BY-SA 4.0 license](https://creativecommons.org/licenses/by-sa/4.0/).
- **Movies/TV — TMDB:** [application authentication](https://developer.themoviedb.org/docs/authentication-application), [movie search](https://developer.themoviedb.org/reference/search-movie), [movie details](https://developer.themoviedb.org/reference/movie-details), [OpenAPI schema](https://developer.themoviedb.org/openapi/tmdb-api.json), [rate limits](https://developer.themoviedb.org/docs/rate-limiting), [FAQ and attribution/SLA information](https://developer.themoviedb.org/docs/faq), and [official status page](https://status.themoviedb.org/).
- **Movies/TV — OMDb:** [API reference](https://www.omdbapi.com/), [key/free-quota page](https://www.omdbapi.com/apikey.aspx), and [Swagger](https://www.omdbapi.com/swagger.json).
- **Video games — RAWG:** [official API/pricing/terms page](https://rawg.io/apidocs). The report flags conflicting free-use wording and redistribution restrictions.
- **Video games — IGDB:** [official API documentation](https://api-docs.igdb.com/) for Twitch authentication, queries and limits. The linked [Twitch developer agreement](https://legal.twitch.com/en/legal/developer-agreement/) did not render substantive terms in the research browser, so exact caching/redistribution permission remained unverified.
- **Music — MusicBrainz:** [API guide](https://musicbrainz.org/doc/MusicBrainz_API), [search reference](https://musicbrainz.org/doc/MusicBrainz_API/Search), [examples](https://musicbrainz.org/doc/MusicBrainz_API/Examples), and [data-license distinctions](https://musicbrainz.org/doc/About/Data_License).
- **Books — Open Library:** [API usage guidelines](https://openlibrary.org/developers/api), [search reference](https://openlibrary.org/dev/docs/api/search), [covers documentation](https://openlibrary.org/dev/docs/api/covers), and [licensing statement](https://openlibrary.org/developers/licensing).
- **Books — Google Books:** [API guide](https://developers.google.com/books/docs/v1/using), [volume search/list](https://developers.google.com/books/docs/v1/reference/volumes/list), [volume fields](https://developers.google.com/books/docs/v1/reference/volumes), [Books terms](https://developers.google.com/books/terms), and [general Google API terms](https://developers.google.com/terms). No universal numeric daily free quota was verified.
- **Additional music screening:** [Apple iTunes Search API](https://performance-partners.apple.com/search-api) and Spotify's [development/quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes) and [rate-limit guide](https://developer.spotify.com/documentation/web-api/concepts/rate-limits). These were screening exclusions, not full endpoint/licensing evaluations comparable to the eight main providers.

### Findings and actual verification

- Saved `research/api-provider-comparison.md` with linked findings on provider authentication, free access/limits, search/detail endpoints, useful fields, local-storage and REST redistribution constraints, and reliability limitations. Distinguished external API credentials from the future app's Django user authentication.
- Recommended **TVmaze**, **Open Library**, and **TMDB**, in that order for this project's practical needs. Proposed a TV watchlist, reading journal and movie diary. TVmaze was easiest because it required no public-search key and offered a short search-to-save workflow. Open Library had work/edition and metadata-completeness tradeoffs; TMDB required credentials/branding and further verification of full storage/redistribution terms.
- A background agent successfully retrieved the official TVmaze `/shows/1` JSON without authentication. This was one sample read, not a completed console-script test or an uptime measurement. The primary agent's separate browser attempts to open some API sample URLs were inaccessible; those attempts did not prove service outages.
- TMDB's FAQ explicitly stated no SLA. The report did not turn missing SLA information for other providers into a claim that no agreement could exist. No accounts were created, provider keys issued, authenticated endpoints exercised, or uptime/latency benchmarks performed during research.

### Summary

- **Outcome:** completed the requested comparison in `research/api-provider-comparison.md` using primary-source links. No application code was implemented in this research session. The user selected TVmaze in the subsequent API-verification prompt recorded above.
- **Deviations:** no user corrections or overrides occurred during research. Background research was delegated as required by the invoked skill.
- **Sideways:** Open Library documentation fetches timed out in some browser calls. TMDB's full terms were blocked to the research browser, and IGDB's linked agreement was not readable; the report retained these as unresolved limitations. RAWG's pricing and terms wording conflicted. These gaps were recorded rather than filled with assumed permissions or invented verification results.

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

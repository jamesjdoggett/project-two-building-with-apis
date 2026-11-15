# PROMPTS.md — AI Usage Log

## 2026-11-14 — ShowVault Phase 3 implementation and approval

### Prompts

User prompts are recorded in conversation order. The initial implementation
request is explicitly summarized; short replies and the logging request are verbatim.

1. Initial `$implement` request (summary): implement only Phase 3 of the approved ShowVault plan after reading AGENTS.md, the PRD, plan, and existing code. Follow its exact scope and acceptance criteria, approved stack, and established conventions; apply meaningful TDD and preserve Phases 1 and 2. Run the full suite, Django checks, Ruff lint/format, and applicable migration checks; fix failures and report actual results. Review AGENTS.md for verified durable additions of 1–7 lines without duplicating requirements. Supply exact browser verification steps and edge cases. Do not implement Phase 4, commit, or modify unrelated features; stop for review.
2. The user supplied the implement skill text. It delegated to the TDD skill and ordinarily required intermediate approval checkpoints and manual verification before finishing; its eventual commit/push step was overridden by the explicit no-commit instruction.
3. "yes all approved do not stop for confirmation." — approved all three proposed TDD behaviors and removed intermediate confirmation pauses.
4. "Update PROMPTS.md with the actual Phase 4 implementation prompts, decisions, test results, manual verification, and fixes. Preserve previous entries. Do not modify other files or run tests. Phase 4 passed verification."
5. "noo i meant phase 3" — corrected both the logging request and verification confirmation to Phase 3.

### Exploration, implementation, and decisions

- Read AGENTS.md, the implement/TDD skills, PRD, approved plan, Independent progress prototype, and existing models, forms, views, routes, templates, operations, provider fixtures, tests, configuration, and documentation. Implemented Phase 3 only: conventional personal editing and local library query controls.
- Selected three TDD behaviors: invalid personal edits preserve every saved value; independent bookmark corrections/rewatch/clearing are visible correctly; combined owner-scoped library controls retain stable pagination and normalized selections. The user approved all three and authorized continuing without intermediate pauses.
- Added persisted rating, notes, watch status, last season, and last episode. Migration `shows.0002_entry_last_episode_entry_last_season_entry_notes_and_more` introduces the fields with Planned, Unrated, blank-note, and absent-bookmark defaults. Migration `shows.0003_entry_valid_personal_rating_entry_valid_watch_status_and_more` adds rating-range, valid-status, and bookmark numeric/pair constraints. A historical-model migration test verifies that existing snapshot fields and timestamps remain unchanged while defaults are added.
- Centralized complete parsed personal-state validation in `shows/personal.py`, including the editable-field allowlist, five statuses, rating/notes boundaries, strict parsed numeric types, and paired bookmark rules. Bookmark input is bounded by SQLite's signed 64-bit integer storage. These rules are available for later API reuse; no API endpoints were implemented.
- Added an owner-scoped GET/POST edit form, explicit clear-bookmark checkbox, field errors, cancel navigation, and successful-save feedback. Valid writes update only personal fields and the local update timestamp; invalid submissions preserve the entire stored record. Reject ownership/provider/unknown fields, JSON/query overrides, and uploaded files. Enforce login, POST mutations, and session CSRF; staff and superusers remain owner-scoped.
- Status and bookmark are independent in every status. Completed corrections retain Completed, returning to Planned retains progress, and explicit clearing retains the chosen status. The form also permits saving two blank numbers to remove a bookmark. No provider episode lookup or automatic completion was added.
- Replaced fixed personal placeholders on detail/library pages with persisted values. Notes retain line breaks and are rendered escaped; forms preserve note whitespace. Repeated discovery saves continue to return the unchanged local entry, including edited personal state, without provider HTTP.
- Added shared `shows.library.library_entries(owner, params)` for local case-insensitive title substring search, status filtering, and recently saved/title/rating sorting. Normalize invalid choices to defaults, trim controls, place Unrated last, and use primary-key tie-breakers. Preserve encoded selections in 20-entry pagination links, use forgiving Django page handling, and distinguish an empty owned library from no matches.
- Updated README with actual checks and detailed browser scenarios, recorded pending review in the plan at handoff, built production CSS, and added two durable AGENTS.md lines identifying the shared personal-validation and library-query callables. No dependencies changed. Refresh, deletion, HTMX, and REST endpoints remain later-phase work; no commits or pushes were made.

### Actual automated verification

| Check | Observed result |
| --- | --- |
| Invalid-edit TDD RED | Posting rating 11 expected HTTP 400 but the scaffold returned 200. The test also requires a rating error and preservation of all stored values, including timestamps. |
| First behavior GREEN and regressions | 93 passed after adding shared validation and the edit form; one pytest cache-write warning. |
| Independent-progress TDD RED | A Completed bookmark correction persisted correctly, but the assertion for `<dd>Completed</dd>` failed because detail still displayed the old Planned placeholder. |
| Second behavior GREEN and regressions | 80 passed after rendering saved personal state; one cache-write warning. The workflow includes Completed/Paused corrections, Planned rewatch, and explicit clearing. |
| Combined-controls TDD RED | The library ignored query/status controls and returned 23 owned entries instead of 21 matches. The test also defines rating ties, Unrated-last ordering, encoded pagination links, and retained controls. |
| Third behavior GREEN and regressions | 81 passed after implementing local controls and retained pagination; one cache-write warning. |
| Expanded Phase 3 tests | 64 passed, including migration defaults, boundaries, database constraints, ownership, CSRF, query normalization, and independent progress; one cache-write warning. |
| Full `uv run pytest` | 226 passed in 50.29 seconds; one existing Windows error 183 cache-write warning for `.pytest_cache/v/cache`. The 64 Phase 3 tests are included in this total. |
| Separate console runner | `uv run python -m unittest discover -s tests -v`: 7 test methods passed, OK. These methods are also collected by pytest, not seven additional distinct tests. |
| Django system check | `uv run python manage.py check`: no issues, 0 silenced. |
| Migration consistency | `uv run python manage.py makemigrations --check --dry-run`: No changes detected. |
| Applied migrations | `uv run python manage.py migrate`: both Phase 3 migrations applied successfully to local SQLite. |
| Ruff lint/format | Final `uv run ruff check .`: All checks passed. `uv run ruff format --check .`: 52 files already formatted. |
| Production CSS | `uv run python -X utf8 manage.py tailwind build`: production stylesheet built successfully. |
| Whitespace | `git diff --check`: no whitespace errors; Git emitted LF-to-CRLF notices. |

These are implementation-session observations. No tests or checks were rerun for
the logging request or its correction.

### Manual verification, fixes, and corrections

- Supplied numbered browser instructions for saved form values and cancel; ratings blank/1/10 and invalid boundaries; 5,000/5,001-character notes; escaped HTML-looking multiline notes; partial/negative/fractional bookmarks; S0 E1; each status; Completed and Paused corrections; Planned rewatch and explicit clearing.
- Documented how to disable native browser validation temporarily and remove the textarea maxlength to exercise server-side rejection. Invalid requests must show actionable errors, retain attempted form values, and leave all stored fields unchanged, including otherwise valid changes in the same submission.
- Reused the existing 21-show `discovery_demo library` fixture to verify combined query/status/sort pagination, retained selections, Unrated-last ordering, deterministic ties, malformed pages, normalized defaults, and distinct empty states. Used `discovery_demo timeout` for local editing/browsing during provider failure without blocking localhost.
- Included second-user/staff cross-owner edit 404s, signed-out login redirects, JavaScript-disabled forms, keyboard/narrow-layout checks, and exact DevTools FormData requests for forbidden owner/title fields (400) and a missing CSRF token (403). Snapshot/retrieval time must remain unchanged by personal edits.
- Browser review was pending at implementation handoff. The user now confirms Phase 3 passed verification, correcting the initial Phase 4 label. No individual scenario observations, screenshots, or post-review product fixes were supplied; no agent-performed interactive browser acceptance is claimed.
- Fixed the failures exposed by the three TDD tests: missing invalid-edit handling, stale personal-state displays, and ignored library controls. Hardened shared status validation so an invalid non-string/unhashable value produces a field error, and bounded bookmarks to prevent storage overflow. Form parsing preserves note whitespace and validation rejects oversized whitespace-only notes too.
- Ruff found one unsorted import block in `shows/views.py`; corrected it and the final full lint/format checks passed. Formatting also normalized the new Python files and generated migrations. The first uv migration command failed because the external cache was inaccessible; an approved escalated run succeeded. The existing pytest cache-write warning remained non-fatal and was not claimed fixed.
- The first documentation follow-up recorded the user's literal Phase 4 label and noted missing Phase 4 evidence. After the user's correction, this new entry was corrected and expanded to cover the actual Phase 3 session. Earlier log entries remain unchanged. Both documentation follow-ups modify only PROMPTS.md; no application files, tests, migrations, or builds were changed or executed during logging.

### Summary

- **Outcome:** Phase 3 implemented, 226 accumulated tests and the separate console suite passed, required checks/build passed, local migrations applied, and the user confirms verification passed. Preserved previous entries; no Phase 4 work, commit, or push was performed.
- **Deviations:** the user approved all selected TDD behaviors and removed further confirmation pauses. The explicit no-commit instruction overrode the skill's finish step. The logging request initially named Phase 4 and was corrected to Phase 3.
- **Sideways:** uv cache access required escalation; TDD assertions exposed the intended missing behavior; an import-order lint finding was fixed; the existing Windows pytest cache warning remained. The mistaken phase label was corrected without inventing Phase 4 work or rerunning tests.

## 2026-11-14 — ShowVault Phase 2 implementation and approval

### Prompts

User prompts are recorded in conversation order. The implementation request is
quoted verbatim with paragraph breaks condensed; the current logging request is
explicitly summarized.

1. "$implement Implement Phase 2 of our approved ShowVault implementation plan. First, read AGENTS.md, the PRD, implementation plan, and existing code. Follow the exact scope and acceptance criteria defined for Phase 2. Use the approved technology stack and follow established project conventions. Apply TDD where appropriate, writing meaningful automated tests for new functionality. Preserve all working functionality from Phase 1. After implementation, run the full test suite, Django system checks, Ruff linting and formatting checks, and any applicable migration checks. Fix any failures and report the actual results. Provide clear manual verification instructions showing exactly what I should test in the browser, including expected behavior and relevant edge cases. Do not implement Phase 3, commit changes, or modify unrelated features. Stop after Phase 2 so I can review and approve it."
2. "yes all selections are approved. do not stop." — approved both proposed TDD behaviors and authorized continuing without further approval pauses.
3. Current review/logging request (summary): "Phase 2 has been manually reviewed and approved." Update PROMPTS.md with actual prompts, decisions, test results, manual verification, and corrections. Review AGENTS.md for only newly verified, durable project-wide guidance, preferably 1–3 lines; avoid repeating the PRD/plan. Do not begin Phase 3.

The user also supplied the implement skill text. It delegated to the local TDD
skill and normally required intermediate approvals and a manual-review boundary.
The user's instruction in prompt 2 removed further intermediate pauses. The
explicit no-commit instruction overrode the skill's eventual commit/push step.

### Exploration, implementation, and decisions

- Read AGENTS.md, the implement/TDD skills, approved PRD and implementation plan, existing models/views/forms/routes/templates/settings, provider client and fixtures, tests, README, dependency configuration, and relevant provider research. No new live provider check was performed in Phase 2.
- Implemented only Phase 2: authoritative saves, independent private snapshots, local detail/library pages, saved discovery indicators, and 20-entry pagination. Root and default post-login navigation now lead to `/library/`. Phase 1 authentication, discovery, CSRF, provider throttling, and console behavior remain covered by regressions.
- Added `Entry` and `shows.0001_initial` with owner, TVmaze ID, snapshot/provenance fields, successful retrieval time, creation/update times, owner/show uniqueness, and a positive-ID constraint. Stored poster URLs only. Personal values display fixed Planned/Unrated/blank-note/no-bookmark defaults; persisted personal fields and editing remain Phase 3 work, following the approved plan.
- Added detail fetching to `shows/tvmaze.py` and extracted shared request handling so search and detail use the same gate, User-Agent, 10-second connection/read timeout, no redirects, and no automatic retries. Validate requested identity and the complete snapshot before saving; missing/null optional fields remain usable, summaries are converted to plain text, and templates escape output.
- Added `save_entry(owner, tvmaze_id)` in `shows/operations.py`, returning `(entry, created)`. An owner-scoped duplicate returns unchanged before HTTP. Authoritative new snapshots use `get_or_create` and database uniqueness to recover competing inserts without overwriting the winner. SQLite locks return a visible committed winner when possible or safe explicit retry feedback; HTTP runs outside write transactions.
- Save uses authenticated CSRF-protected POST and rejects extra ownership, provider, personal, URL, query, or JSON inputs. Invalid IDs fail before HTTP. All list/detail/save selection is owner-scoped, including staff and superusers; foreign and missing local detail IDs return 404.
- Added local templates for detail, library, and save errors with source/license/transformation attribution, placeholders, and existing failed-poster handling. Added `library` and `invalid-detail` scenarios to the DEBUG-only loopback `discovery_demo` command for 21 synthetic search/detail fixtures and invalid save-time detail responses. Synthetic entries persist only when explicitly saved by a user; no accounts or entries are automatically seeded.
- Updated README with exact browser steps and actual automated results, and recorded implementation/pending review in the plan at handoff. Added one durable authoritative-save instruction to AGENTS.md during implementation. No dependencies changed; no Phase 3 editing, refresh/deletion, query controls, HTMX, or REST endpoints were added.

### Actual automated verification

| Check | Observed result |
| --- | --- |
| Authoritative-save TDD RED | Assertion expected a 302 detail redirect but the scaffold returned 400. The test also defines snapshot/provenance storage, authenticated ownership, provider request parameters, and displayed defaults. |
| Authoritative-save GREEN and regressions | 67 passed; one pytest cache-write warning. |
| Repeat-save TDD RED | Failed on `AssertionError: Repeat save must not use HTTP` when the existing entry still triggered detail fetching. |
| Both selected TDD behaviors GREEN | 2 passed after adding the local duplicate lookup; one cache-write warning. Repeat save preserved every stored field and timestamp. |
| Expanded Phase 2/authentication checks | 90 passed; one cache-write warning. |
| Final `uv run pytest` | 162 passed in 33.55 seconds; one Windows error 183 cache-write warning for `.pytest_cache/v/cache`. The existing console methods include 13 subtest cases; these are not 13 additional distinct application tests. |
| Concurrency and collision coverage | Passing tests coordinate two initial misses on genuinely separate SQLite connections with transaction-enabled pytest coverage; verify one winner, safe lock outcomes, and local duplicate retry. Separate tests exercise a real unique-constraint collision and recovery, explicit lock feedback, and returning a committed winner. Sequential duplicate coverage is not presented as concurrency evidence. |
| Separate console runner | `uv run python -m unittest discover -s tests -v`: 7 test methods passed, OK; these are also collected by pytest. |
| Django system check | `uv run python manage.py check`: no issues, 0 silenced. |
| Migration checks/application | `uv run python manage.py makemigrations --check --dry-run`: No changes detected. `uv run python manage.py migrate`: `shows.0001_initial` applied successfully. |
| Ruff lint/format | Final `uv run ruff check .`: All checks passed. `uv run ruff format --check .`: 45 files already formatted. |
| Production CSS | `uv run python -X utf8 manage.py tailwind build`: production stylesheet built successfully. |
| Locked dependencies | `uv sync --locked`: resolved 22 packages and checked 21 installed packages successfully. |
| Whitespace | `git diff --check`: no whitespace errors; Git emitted LF-to-CRLF notices. |

Other passing coverage includes timeout/connection/404/429/5xx/redirect/JSON/shape
failures, invalid required and optional field types, provider-ID mismatches,
forged inputs, optional-field placeholders, shared discovery/save throttling,
independent owners, staff/superuser isolation, no-HTTP local rendering, escaping,
20/1 pagination and page normalization, authentication, POST-only save, and CSRF.

### Manual verification and corrections

- Supplied numbered browser instructions for setup/sign-in, search/save/detail/defaults/provenance, unchanged repeat saves and saved indicators, independent second-user entries, foreign detail 404s including staff, 21-entry pagination, absent/broken posters, timeout outages, invalid new-save detail responses, JavaScript-disabled forms, and POST-only behavior.
- The fixtures make provider outages and invalid details deterministic without blocking localhost. Instructions keep a discovery results tab open before switching servers, so an existing save form can prove repeat saving remains local during an outage. Dedicated ordinary accounts keep the 21 synthetic shows separate from real saved shows.
- At implementation handoff, interactive browser verification was explicitly pending; automated template checks were not described as browser verification. The current user now explicitly confirms Phase 2 was manually reviewed and approved. No individual scenario results, screenshots, or requested product fixes were supplied, so no additional per-scenario observations are invented. No post-review product corrections were requested or made.
- During implementation, corrected optional text validation so malformed false/empty-container values are rejected instead of silently treated as missing. Updated authentication regressions to expect the Phase 2 library destination and replaced the obsolete no-library assertion with checks that unfinished actions remain absent.
- Ruff initially reported long lines in generated migrations, tests, operations, and fixtures. Formatting fixed most; one remaining fixture summary line was wrapped and lint then passed. Initial uv commands failed on access to the external cache; escalated runs succeeded. The pytest cache-write warning remained on the final run and is recorded rather than claimed fixed.
- This documentation-only follow-up preserves prior log entries and refines the existing AGENTS.md save instruction with its verified callable/return contract and `SaveBusy` behavior. No redundant architecture section or new phase-specific requirements are added. Application checks are recorded from implementation, not claimed rerun for this logging task.

### Summary

- **Outcome:** Phase 2 implemented, automated checks passed with the recorded cache warning, local migration applied, and user confirms manual review and approval. No Phase 3 work, commit, or push was performed.
- **Deviations:** after approving TDD selections, the user explicitly removed further approval pauses; the agent retained the Phase 2/manual-review boundary. The user subsequently asked for a faster handoff, which the agent acknowledged.
- **Sideways:** uv cache permissions required escalation; initial lint/format findings were fixed; the final pytest cache warning remained non-fatal. No failed attempt is counted as a passing check, and no live API or agent-performed browser verification is claimed for Phase 2.

## 2026-11-14 — ShowVault Phase 1 implementation and review

### Prompts

User prompts are recorded below in conversation order. Long documentation requests are explicitly summarized; short approvals are verbatim.

1. Initial AGENTS.md request (summary): create a root guidance file following ATS's incremental approach, between 20 and 30 lines, with application description, approved stack, uv workflow, confirmed architecture, and actual PRD/plan/research/prototype references. Avoid duplicated requirements, speculative guidance, unverified commands, and rejected options. During implementation preserve only verified project-wide conventions with small additions; implement no features yet and report the line count.
2. "$implement Implement Phase 1 of the approved implementation plan for our TV show tracking application. Read AGENTS.md, the approved PRD, implementation plan, and relevant prototype decisions before making changes. Follow the established technology stack and use the existing uv environment. Implement only Phase 1, following the phase's acceptance criteria. Add appropriate automated tests and run the relevant tests, Django checks, Ruff linting, and formatting checks. Report the actual results and any issues. Give me clear manual verification instructions, including how to run the application and what behavior I should test. Do not start the next phase, modify unrelated features, or commit anything until I have reviewed and approved the work."
3. "appropved" — approved the proposed TDD behaviors: blank search must not call the provider; timeout must show retry guidance and retain the query.
4. "yes" — approved the first failing blank-search test before implementation.
5. "yes" — confirmed the passing blank-search behavior before proceeding to timeout handling.
6. "yes" — approved the failing timeout test before implementation.
7. Review/logging request (summary): "Phase 1 has been reviewed." Update PROMPTS.md with the actual implementation session, significant prompts, decisions, tests, manual verification, and requested fixes; preserve prior entries. Review AGENTS.md for essential new verified project-wide guidance, adding preferably 1–7 lines. Do not begin Phase 2.

The attached implement skill delegated to the local TDD skill, which initially required separate selection, failing-test, and passing-behavior approvals. The user's subsequent automation instruction superseded further TDD approval pauses for this feature.

### Exploration, implementation, and decisions

- Read root guidance, the implement/TDD skills, approved ShowVault PRD and plan, selected progress prototype, TVmaze research, existing console code/tests and uv configuration, and relevant adjacent ATS configuration/styling patterns. Rechecked official TVmaze, Django authentication, and django-tailwind-cli documentation during integration.
- Initially created AGENTS.md at 28 lines. During implementation replaced its stale not-implemented statement with verified layout guidance and added checks/setup commands, bringing it to 30 lines before the current logging update.
- Used the existing uv environment and lockfile. Installed Django 5.2.19, django-tailwind-cli 4.8.2, pytest 9.2.0, and pytest-django 4.14.0 alongside existing requests/Ruff. Introduced `config/`, one `shows/` app, pytest discovery and Ruff configuration, and applied Django's built-in account/admin/session migrations. No persisted show model or application-specific migration was needed in Phase 1.
- Implemented Django session login for ordinary active users, protected welcome/discovery pages, POST logout with CSRF, styled authentication feedback, and Django admin account creation. Used built-in authentication redirect protections; ordinary users cannot access admin. No public signup or seeded credentials were added.
- Delivered submitted GET discovery with all provider results in relevance order, title/year/summary/poster rendering, loading feedback, optional-field placeholders, escaped plain text, TVmaze source links, and CC BY-SA/transformation attribution. Used a shared base template, Tailwind/DaisyUI CSS, a local poster placeholder, and small local JavaScript for loading and broken-image fallback. HTMX interaction behavior remains a later-phase feature.
- Implemented the official server-side search boundary in `shows/tvmaze.py`: encoded query parameters, identifying User-Agent, 10-second connection/read timeouts, response validation, useful provider errors, and no automatic retry. Its thread-safe shared gate allows one outbound request per second in a single local server process and honors Retry-After seconds/HTTP dates after 429 responses. It does not coordinate multiple processes.
- Added `discovery_demo` as a DEBUG-only loopback development command for timeout, rate-limit, malformed, no-results, and missing-data scenarios. Fixtures intercept provider HTTP only in that process; there are no public fixture switches or arbitrary provider URLs. The missing-data fixture includes both absent and broken images.
- Expanded README with setup, account creation, normal running, checks, numbered browser scenarios, and deterministic fixture instructions. Recorded Phase 1 as awaiting manual verification in the plan at handoff; did not mark its acceptance checkboxes complete or start Phase 2. The existing console script received only a line-wrap change to satisfy the newly configured Ruff line-length rule.

### Actual automated and integration verification

| Check | Observed result |
| --- | --- |
| First TDD blank-search RED | Assertion failed because the provider boundary was called once with an empty string. |
| Blank-search GREEN and regressions | 8 passed, 13 subtests passed after adding the trim/blank guard and useful feedback. |
| Timeout RED | Assertion expected HTTP 200 but received HTTP 500 from the uncaught simulated timeout. |
| Timeout GREEN and regressions | 9 passed, 13 subtests passed after catching the timeout and retaining the query. |
| Initial expanded pytest suite | 1 failed, 71 passed, 13 subtests passed; result-count pluralization rendered incorrectly. Fixed the template suffix. |
| Intermediate expanded suite | 75 passed, 13 subtests passed, with one pytest cache-write warning. |
| Final full pytest run | 79 passed, 13 subtests passed in 10.21 seconds; no warning reported. The suite covers account creation/access, login redirects, CSRF/logout methods, search validation/rendering, escaping, HTTP/data failures, shared throttling across users/threads, Retry-After, and all fixture scenarios. |
| Separate console unittest runner | 7 test methods passed, OK; these console behaviors are also collected by pytest, not seven additional distinct application tests. |
| `uv sync --locked` | Passed: resolved 22 packages and checked 21 installed packages. |
| Ruff lint and formatting | Final lint: All checks passed. Final format check: 41 files already formatted. |
| Django checks | System check identified no issues; migration consistency reported No changes detected. Built-in migrations were applied successfully to local SQLite. |
| Production CSS build | Passed using the standalone Tailwind/DaisyUI executable through django-tailwind-cli; final elevated build completed successfully. |
| Local HTTP smoke checks | Anonymous `/` and `/discover/` returned 302; login returned 200; CSS, JavaScript, and placeholder SVG returned 200 with appropriate content types. The fixture server's login page also returned 200. Servers were stopped after checking. |
| Live provider-client search | Final UTF-8 run exited 0, returning five Firefly-related matches, including an international title. This is one live search, not an uptime guarantee or a five-result application cap. |
| Whitespace check | `git diff --check` reported no whitespace errors; Git emitted LF-to-CRLF notices. |

### Manual verification and requested fixes

- At handoff, supplied commands for locked uv setup, migration, CSS build, superuser creation, and development-server startup. Directed the user to create two ordinary users in admin and test authentication, wrong credentials, blocked admin access, discovery success/blank/no-match cases, attribution, POST sign-out, JavaScript fallback, loading feedback, keyboard/narrow-window layout, and deterministic provider failures/missing posters.
- The agent performed HTTP smoke checks and automated tests, not interactive browser verification. Broken-poster replacement and visual/loading behavior were explicitly left for browser review.
- The current user message states, "Phase 1 has been reviewed." No individual browser scenario outcomes, screenshots, or requested manual-review fixes were supplied in this conversation. Record that review without inventing a claim that every browser scenario passed. No post-review feature fixes were requested or made.
- This logging task adds two essential AGENTS.md conventions: reuse the verified single-process provider gate, and use the verified local fixture command for browser failure checks. Existing stack, layout, setup/check commands, and approved references remain intact. No implementation checks were rerun for this documentation-only update.

### Summary

- **Outcome:** Phase 1 authentication/discovery implemented and tested; startup/manual verification instructions supplied; user reports the phase reviewed. Preserved previous log entries and added only essential verified guidance. No Phase 2 work, commit, or push was performed.
- **Deviations:** the user approved the TDD selections/cycles, then explicitly removed further approval pauses for the feature. Manual review and commit boundaries remained. No user-requested product-scope changes or review fixes occurred.
- **Sideways:** uv cache access and network restrictions required escalation for dependency installation and uv checks; uv fell back from hardlinks to copies. An initial patch was rejected for multiple operations targeting one file and was reapplied correctly. Early Ruff checks found generated unused imports, import order, formatting, and long lines; these were corrected. An expanded test caught incorrect match pluralization, which was fixed. One pytest cache-write warning did not recur. Sandbox restrictions blocked the first Tailwind download and later execution of its downloaded binary; elevated runs succeeded. The first live client attempt was blocked by networking; an elevated attempt fetched results but failed printing international text under Windows cp1252. Re-running with `python -X utf8` succeeded. None of those failed attempts is counted as a passing check.

## 2026-11-14 — Approved six-phase ShowVault implementation plan

### Prompts

1. "$prd-to-plan Read prd/showvault.md, the approved prototype, and the TVmaze research. Create a phased implementation plan following the same engineering approach used in my Applicant Tracking System project. Each phase must be small enough for one coding session and deliver working, testable functionality. Include automated tests, manual verification scenarios, and acceptance criteria for every phase. Introduce models, views, templates, and tests together in usable vertical slices. Do not implement anything yet."
2. "uh yeah no. lets condense that into 6 phases"
3. "yes approved and update PROMPTS.md"

The attached `prd-to-plan` skill supplied the vertical-slice workflow and required approval of the proposed breakdown before writing the plan.

### Exploration, decisions, and artifacts

- Read the ShowVault PRD, progress prototype, TVmaze provider research, existing README and dependency configuration, and the adjacent ATS project's plan, guidance, dependency configuration, routes, forms, view patterns, and authentication tests. No new external research or live API verification was performed.
- Initially proposed twelve phases and requested the skill-required breakdown review. The user rejected that granularity and requested six phases. Proposed a condensed breakdown, which the user explicitly approved before file creation.
- Created [plans/showvault.md](plans/showvault.md) with the approved phases: authentication/discovery; saving/private local libraries; personal editing/library navigation; refresh/deletion/HTMX; API reads/creation/updates; API refresh/deletion and complete workflow verification.
- Recorded durable architecture, named and namespaced route paths, one shows app, owner-scoped per-user snapshots, shared save/refresh/validation/query behavior, database constraints, session authentication and CSRF, provider boundaries, error mapping, provenance, and final Independent bookmark rules. Proposed route spelling, model name, and explicit PUT semantics are planning decisions, not additional interview answers.
- Each phase includes user-story references, end-to-end scope, automated tests, manual scenarios, and checkbox acceptance criteria. Coverage maps account for all 18 PRD stories and acceptance criteria. Tests and manual checks are planned requirements, not reported passing results.
- Preserved the ATS approach of conventional Django vertical slices, incremental styling, per-phase regression/build checks, and browser-verifiable functionality while retaining ShowVault's ordinary-user and private-owner access requirements.

### Summary

- **Outcome:** saved the approved six-phase plan and updated this log while preserving prior entries. No application implementation or dependency changes were made.
- **Deviations:** the user replaced the initial twelve-phase proposal with six phases and approved the revised breakdown. The plan identifies phases 3 and 4 as the broadest sessions and bounds them through conventional forms and reuse.
- **Sideways:** no failed edit commands occurred. Some exploration output was truncated by tool output limits; no missing output was treated as verification. No application tests, browser checks, migrations, CSS build, or live provider requests were run in this documentation-only session.

## 2026-11-14 — ShowVault interview, progress prototype, and PRD

### Prompts

User prompts below are in conversation order. The first prompt is summarized explicitly; quoted short replies are verbatim. Attached skill instructions supplied the interview, prototype, and PRD workflows rather than additional product requirements.

1. Initial `$grill-me` request (summary): design ShowVault, a personal TV tracker using Django, DRF, SQLite, uv, Ruff, Tailwind/DaisyUI through django-tailwind-cli, HTMX, and pytest/pytest-django following the previous ATS project. Required external TVmaze search, local metadata snapshots, personal ratings/notes/status/progress, private searchable/filterable/sortable/paginated library, own CRUD API, consistent authentication/ownership, and graceful request failure handling. Read existing research and the API verification script before interviewing; ask one question at a time with tradeoffs; pause for at least one meaningful `$prototype`; do not write a PRD or implement yet.
2. "go with option 2 and use prototype" — selected last-watched season/episode rather than total episodes watched or individual episode checklists.
3. "I'll go with independent. Continue with the rest of the grill me questions." — selected independent status/bookmark rules after the prototype was supplied.
4. "option 2" — selected Planned, Watching, Paused, Completed, and Dropped.
5. "recommended option" — administrator-created ordinary accounts, rather than public registration.
6. "recommended option" — one saved entry per user per show, rather than separate rewatch entries.
7. "recommended option" — optional whole-number personal rating from 1–10.
8. "recommended option" — local metadata snapshot with explicit manual refresh.
9. "recommended option" — separate metadata snapshot per user entry, rather than a shared show catalog.
10. "recommended option" — poster URLs with a local placeholder, rather than downloaded images.
11. "recommended option" — submitted discovery search, rather than search-as-you-type.
12. "recommended option" — save immediately as Planned, then open the detail page.
13. "recommended option" — session authentication for website and API, rather than adding tokens.
14. "recommended option" — API creation from a TVmaze ID with server-fetched metadata.
15. "recommended option" — title search, status filter, recently saved/title/rating sorting, and 20 entries per page.
16. "recommended option" — permanent deletion with website confirmation, rather than trash/restore.
17. "recommended option" — manual bookmarks without episode lookup: both fields set or both blank, season >= 0 and episode >= 1.
18. "recommended option" — optional private plain-text notes, maximum 5,000 characters.
19. "recommended option" — no automatic retries, preserved query, and a 10-second connection/read timeout.
20. "recommended option" — dedicated owner-protected API metadata-refresh action.
21. "just go with the recommended option for the remainder of the questions" — accepted the pending duplicate API-save recommendation and delegated remaining choices. The agent stopped interviewing and summarized recommended defaults.
22. "$to-prd Create a complete Product Requirements Document for ShowVault using our completed interview, selected prototype, and TVmaze research. Include all assignment requirements, user stories, implementation decisions, validation rules, authentication and ownership policies, local metadata storage, external API error handling, and acceptance criteria. Do not implement the application yet."
23. "Update PROMPTS.md with the actual $grill-me interview, $prototype design comparisons, decisions, and $to-prd session. Do not invent prompts or results. Preserve existing entries."

### Exploration and prototype

- Read the existing TVmaze research, console verification script and tests, README, and dependency configuration. Read the adjacent ATS project's guidance, dependencies, and README for its conventional Django, local assets, HTMX, Tailwind/DaisyUI, pytest, and Ruff conventions. No new live provider verification was performed.
- Created [watch-progress.html](prototypes/watch-progress.html), a standalone, memory-only HTML/CSS/JavaScript logic prototype with free-play controls and tabbed guided walkthroughs. This compared business rules, not visual interface variations.
- **Assisted:** saving progress changes Planned or Completed to Watching; choosing Planned clears the bookmark. Correcting progress preserves Paused and Dropped.
- **Independent:** saving, correcting, or clearing a bookmark never changes status; changing any status never changes the bookmark. The agent recommended this to preserve user intent, and the user explicitly selected it.
- Walkthroughs cover starting, pausing/resuming, completing then correcting, planning a rewatch, and specials/invalid numbers. The comparisons expose automatic reopening after a correction and automatic bookmark clearing under Assisted rules. Relevant state and feedback are rendered after actions.
- The artifact initially selects Assisted and labels some statuses exploratory. The subsequent PRD explicitly records the final Independent decision and five approved statuses. Prototype code is throwaway, not production architecture.
- The agent did not open or exercise the prototype in a browser and wrote no prototype tests. The user's selection is recorded; which walkthroughs the user personally ran is unknown.

### Decisions and PRD

- Accounts are created by administrators through Django admin; ordinary users need no staff status. Require login for discovery and all library/HTMX/API operations. Use Django sessions and CSRF-protected writes. Owner-scope all queries and return 404 for another user's entry, including refresh/delete. Staff using ordinary application endpoints remain owner-scoped.
- One entry per user/TVmaze show ID, with separate local metadata and personal fields. Repeated saves open/return the existing entry unchanged before contacting TVmaze. API creation returns 201 for new entries and 200 for duplicates.
- Save new entries as Planned, Unrated, blank notes, and no bookmark. Ratings are optional integers 1–10; notes are optional private plain text up to 5,000 characters. Bookmarks identify the last episode finished: whole season >= 0 (specials use 0) and episode >= 1, both present or both absent. No episode lookup or automatic completion. Status and progress remain independent.
- Store TVmaze ID/source link, title, plain-text summary, genres, language, premiere/end dates, provider show status, poster URL, and retrieval timestamp. Preserve attribution/provenance in website/API output and escape notes/summaries. Missing optional data gets placeholders; images are not downloaded.
- Refresh is explicit and changes only that entry's provider metadata. Failure preserves the last good snapshot and personal values. Saved browsing, personal editing, and deletion remain usable without TVmaze.
- Discovery uses submitted searches and relevance-ordered results with saved indicators. Local library controls are title search, status filtering, recently saved (default)/title A–Z/highest personal rating sorting, Unrated last, and 20-entry pagination retaining query controls.
- API supports CRUD plus refresh, uses server-fetched metadata for creation, and accepts only personal fields on ordinary updates. Website deletion requires confirmation and protected POST; API DELETE acts immediately after authorization. Re-saving a deleted show starts fresh.
- Failures distinguish empty results from timeouts, HTTP/rate-limit errors, connection failures, invalid JSON, and malformed data. Preserve input/data, use a 10-second connection/read timeout, and do not retry automatically.
- Under the user's delegated defaults, the agent recommended one shows app plus Django configuration, a small provider client, shared save/refresh and validation logic, consistent library/API query controls, and meaningful mocked-provider tests. These were summarized defaults, not separately answered interview questions.
- Created [the PRD](prd/showvault.md), with assignment coverage, 18 user stories, implementation decisions, validation, access policies, storage, website/API behavior, external failures, 18 acceptance criteria, exclusions, and reference notes.
- PRD synthesis adds specific implementation details such as deterministic sort ties, concurrent duplicate protection, atomic refreshes, HTMX login-expiry handling, a small shared request throttle, and error mapping (504 timeout, retryable 503 rate limit, 502 other upstream failures, 400 invalid ID on new creation). These were not individually interviewed choices.

### Actual verification and limitations

- Prototype and PRD file-creation calls succeeded. A file inspection reported the PRD as 23,313 bytes; Git status showed the PRD and prototype directories untracked.
- `git diff --check` after PRD creation reported no whitespace errors, but did not check the new untracked artifacts. It does not establish application or prototype correctness.
- No application code, dependencies, migrations, automated application tests, browser tests, CSS build, new live API checks, or deployment were performed in this design/PRD session.

### Summary

- **Outcome:** completed the interview, created the logic comparison, recorded Independent bookmark behavior, and saved a complete ShowVault PRD. No Django application was implemented.
- **Deviations:** the user accepted recommended choices, explicitly selected Independent, then requested recommended defaults for remaining decisions. The PRD was written only after a separate request.
- **Sideways:** a higher-level directory listing for guidance was denied; reading the adjacent ATS project directly succeeded. The prototype retains exploratory/default wording, distinguished from final requirements in the PRD. During this logging task, an attempted Python-based prepend failed because the shell's python.exe could not run; it made no file change, and the entry was added with a patch instead.

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

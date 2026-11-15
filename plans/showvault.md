# Plan: ShowVault

> Source PRD: [ShowVault](../prd/showvault.md).
>
> Status: six-phase breakdown approved by the user on 2026-11-14. Phases 1 and 2 have been implemented; Phase 3 is implemented and awaiting browser review. Phases 4–6 have not started. Phase 3 changes remain uncommitted as requested.
>
> References: [progress prototype](../prototypes/watch-progress.html), [TVmaze research](../research/api-provider-comparison.md), and the adjacent [ATS implementation plan](../../applicant-tracking-system/plans/applicant-tracking-system.md).

## Architectural decisions

- **Stack and ownership**: Python 3.14, Django, DRF, SQLite, uv/lockfile, Ruff, pytest/pytest-django, Tailwind/DaisyUI through django-tailwind-cli, and locally served HTMX. One `shows` application and a configuration package. Resolve compatible versions during implementation rather than copying ATS pins blindly.
- **ATS approach**: conventional Django models, forms, views, templates, authentication, and account admin; simple server-rendered screens, incremental styling, database constraints, submission-time validation, and protected POST mutations. Reuse the engineering approach, not ATS's staff-only/shared-record permissions. No separate frontend or large service architecture.
- **URLs**: named, app-namespaced website routes at `/library/`, `/library/<int:pk>/`, `/library/<int:pk>/edit/`, `/library/<int:pk>/refresh/`, `/library/<int:pk>/delete/`, `/discover/`, and `/discover/<int:tvmaze_id>/save/`. Root redirects to the library. Use `/accounts/login/`, `/accounts/logout/`, and `/admin/`. Namespaced API routes at `/api/entries/`, `/api/entries/<int:pk>/`, and `/api/entries/<int:pk>/refresh/`. Local primary keys identify saved entries; provider IDs identify discovery selections. Query parameters are `q`, `status`, `sort`, and `page`; discovery uses `q` separately.
- **Entry model**: `Entry` belongs to Django's existing user model through an owner foreign key. Each user/show pair has its own metadata snapshot; no shared catalog or M2M is needed. Enforce database uniqueness on owner plus positive TVmaze ID. Store the PRD's provider metadata, provenance, successful retrieval time, local timestamps, and personal fields. Introduce the model and snapshot migration in phase 2, personal editing fields in phase 3; add bookmark constraints when those fields arrive. New entries are Planned, Unrated, blank notes, and no bookmark throughout.
- **Constraints and policy**: optional integer rating 1–10; notes at most 5,000 characters; exactly five approved statuses; bookmark both absent or whole season >= 0 and episode >= 1. Use shared validation plus suitable database numeric/pair constraints. Status and bookmark remain independent, including Completed corrections and Planned rewatches. Never verify episode existence or infer completion. The PRD's final Independent policy overrides the prototype's Assisted default and exploratory labels.
- **Access**: administrators create ordinary accounts; public registration is absent. All website, fragment, and API access requires authentication. Scope entries to the requester before lookup, including for staff and superusers using ordinary endpoints; missing and foreign entries return 404. Set ownership server-side and reject submitted ownership changes. Account admin need not expose entries.
- **Mutations and sessions**: website changes and logout use CSRF-protected POST; GET never mutates. DRF uses session authentication and authenticated-user permissions with CSRF enforcement for unsafe requests. Anonymous API access returns a DRF error, never an HTML login redirect; session authentication may return 403. Expired HTMX sessions navigate to login instead of inserting login markup.
- **Shared operations**: keep the provider client small. Share save/refresh operations, personal validation, and normalized owner-scoped library queries across forms and serializers. Duplicate save returns the existing entry unchanged before networking; database-backed collision handling prevents duplicate rows and unhandled integrity errors. Save and refresh accept IDs, never arbitrary fetch URLs or client metadata.
- **Provider boundary**: official search/detail endpoints only, encoded parameters, identifying User-Agent, 10-second connection/read timeout, no automatic retries, and a small shared throttle suitable for this local deployment. Share its budget across search/save/refresh. Honor provider wait guidance. Validate status, JSON, shape, required display data, and requested detail identity before persistence. Do not hold database write transactions open while waiting on HTTP.
- **Persistence and presentation**: new save and refresh are all-or-nothing. Refresh updates provider fields and successful retrieval time only, preserving personal fields and creation time. Convert provider summaries to plain text; escape summaries and notes, preserving note line breaks. Store image URLs only and provide a local placeholder for absent or failed posters. Present TVmaze source/license/transformation provenance on detail pages and in API representations; preserve attribution wherever provider content is displayed.
- **Library behavior**: case-insensitive title substring search, one status filter, recently saved default/title A–Z/highest personal rating sorts, Unrated last, and deterministic primary-key tie-breaking. Normalize invalid filter/sort values to defaults, paginate at 20, and retain normalized selections. Use conventional forgiving Django pagination for malformed/out-of-range pages. Share HTML fragments/context between full and HTMX responses.
- **API write contract**: create accepts TVmaze ID only, returning 201 for new and 200 for unchanged duplicate entries. PUT/PATCH accept personal fields only and reject owner/provider-field writes. PATCH validates the resulting bookmark pair against existing values; clearing requires both null. PUT requires all personal fields, with explicit null/blank values for optional ones, and is documented as replacement of personal state only. Delete returns 204; refresh is explicit POST returning 200.
- **Error contract**: validation 400, owner-scoped not found 404, timeout 504, upstream rate limit retryable 503 with wait guidance, other upstream/invalid-data failures 502. Provider detail 404 is invalid-show-ID 400 on creation and removal/unavailability 502 on refresh. Use structured API errors and useful website feedback without raw provider HTML or tracebacks.

## Working and verification rules

- The approved six phases are sequential, each targeting one coding session. Keep screens modest and reuse earlier behavior to contain scope. Every phase ends with usable functionality, automated coverage, and a manual demonstration; no separate model-only, API-client-only, styling, or testing phase.
- Introduce necessary models/migrations, forms or serializers, views, templates, styling, and tests together. Later phases extend the existing model without inventing migrations where no schema change is needed. Phase 1 discovery is legitimately read-only and introduces no saved-entry model.
- Each phase runs focused tests and accumulated regressions, Ruff lint/format checks, Django system checks, migration consistency checks, and a production CSS build. Apply new migrations to local SQLite. Record actual results and remaining issues; do not label planned checks as passed.
- Use pytest/pytest-django and mocked HTTP responses for deterministic integration tests. Exercise real owner-scoped request paths, form/serializer errors, database constraints, no-network local operations, and CSRF with enforcement enabled. Keep the console unittest verification running separately; do not inherit its five-result application limit or arbitrary URL override.
- Manual fixtures and controlled provider failures are development-only demonstrations, not public failure switches. Live searches may supplement acceptance but never gate deterministic tests. Review the research's official TVmaze and license references during integration; this plan makes no new claims of live verification or provider availability.
- Do not link unfinished actions. Preserve the PRD exclusions: no tokens, public signup, shared catalog, episode sync, background refresh, automatic retry, downloaded posters, or deployment infrastructure. The PRD's exclusion of planning applied to its earlier document-creation task; the current user request authorizes this plan.

---

## Phase 1: Authentication and TVmaze discovery

**User stories**: 1–4, 17, 18 (saved indicators from story 4 arrive with persistence in phase 2).

**Review status**: implemented and awaiting the user's browser verification; not yet complete or committed. Automated verification: 79 pytest tests plus 13 subtests pass, the separate 7-method console unittest suite passes, and Django system/migration checks, Ruff lint/format, locked uv sync, applied built-in migrations, and the production CSS build pass. HTTP smoke checks verified anonymous redirects, login, and static assets; a live client search returned five Firefly-related results. Browser layout, loading feedback, failed-poster replacement, and the manual account/search walkthrough remain for user review. An intermediate pytest cache-write warning did not recur on the subsequent full run. See README for run and deterministic failure-demo instructions.

### What to build

Bootstrap the required Django/uv stack, CSS build, pytest configuration, and shared styled layout. Administrators create active ordinary users in admin. Deliver login, protected landing page, POST logout, and a conventional submitted discovery form. Search displays the provider's finite results in relevance order with title, known premiere year, plain-text summary, poster fallback, and attribution. Introduce the search client and shared throttle through this screen. Trim blank input before networking; retain queries on no matches or service failure. HTMX enhancement is deferred to phase 4; ordinary discovery works now.

### Automated tests

- Admin-created non-staff accounts can sign in; bad credentials/inactive accounts fail; anonymous discovery redirects to login; ordinary users cannot use admin. Login/logout enforce CSRF and logout rejects GET; external `next` values cannot redirect off-site.
- Assert encoded query parameters, identification, timeout, relevance order, more than five returned results, blank-input no-request behavior, valid empty results, optional-field placeholders, and escaped summary output.
- Mock timeout, connection error, 429 with wait guidance, other HTTP errors, invalid JSON, and malformed result structures. Verify useful messages and retained query. Test shared throttle with controlled time and no automatic retry.

### Manual verification scenarios

1. Create two ordinary accounts in admin; sign in with each, submit a discovery query, sign out, and attempt discovery anonymously. Check styled login errors and keyboard operation.
2. Search for a recognizable title and a no-match phrase. Submit whitespace; then use controlled timeout/429/malformed-response fixtures. Confirm distinct feedback and retained input. Block a poster URL and verify the local fallback.

### Acceptance criteria

- [ ] Ordinary accounts can discover shows without staff access; anonymous requests require login and logout is protected POST.
- [ ] Nonblank search renders complete ordered results without an invented five-result cap or external pagination; blank input sends no request.
- [ ] Missing optional fields and failed images have usable fallbacks; provider HTML is never trusted.
- [ ] Empty results are normal, failures are actionable, queries remain visible, and requests use the shared bounded client policy.
- [ ] Phase tests, accumulated checks, CSS build, and manual scenarios pass with results recorded.

---

## Phase 2: Saving shows and private local libraries

**User stories**: 5–7, 17; saved indicators complete 4.

**Review status**: implemented and awaiting the user's browser verification, with no commit or push. Actual automated results: 162 pytest tests (plus 13 console subtests) and the separate 7-method console unittest suite pass; Django system checks, migration consistency, Ruff lint/format, applied `shows.0001_initial`, and production CSS build pass. Pytest reports a Windows cache-write warning without test failures. Both selected TDD behaviors were red before implementation and green afterward. Tests include real competing saves on separate SQLite connections, unique-collision recovery, lock feedback, owner/staff isolation, provider failures, and local pagination/rendering without HTTP. Personal fields remain fixed displayed defaults until phase 3, as planned. See README for exact browser scenarios and deterministic fixtures; manual verification is not yet claimed.

### What to build

Introduce `Entry`, its owner relationship, metadata snapshot, provenance, timestamps, and database owner/show uniqueness. Save from discovery through protected POST using authoritative detail data. Open the new entry's local detail page and list it in a basic 20-entry paginated library, now the post-login destination. Show saved indicators on discovery results. Existing entries open unchanged before contacting TVmaze. Deliver safe handling of duplicate races and independent snapshots for different owners. Personal values display their fixed initial defaults until editing arrives in phase 3.

### Automated tests

- New save fetches the requested detail ID and stores all PRD snapshot/provenance fields and defaults; forged ownership/metadata/URL input is rejected. Invalid/nonpositive IDs and provider-ID mismatches fail safely.
- Cover detail timeout/connection/404/429/5xx/invalid JSON/shape and required-field failures: no partial row is created; optional missing fields remain valid.
- Duplicate save returns the same row unchanged without HTTP even during failure; verify database uniqueness and collision-recovery behavior. Exercise competing creates with separate transactions/connections where SQLite permits, accounting for locking without accepting an unhandled integrity error; do not treat a sequential duplicate test as concurrency evidence.
- Two users save the same show independently; owner-scoped list/detail/save selection, including staff sessions, cannot disclose other entries. Foreign and missing local IDs yield 404.
- Patch provider calls to fail on list/detail; verify local rendering, provenance, pagination and defaults, no network calls, POST-only save, and CSRF.

### Manual verification scenarios

1. Search, save, inspect the local detail and library, repeat save, and observe the saved indicator. Confirm repeat save works with TVmaze blocked and preserves the original snapshot/retrieval time.
2. Save the same show as the second user and compare independent entries. Try the first user's detail URL as the second user and as staff. Browse 21 local entries and verify page boundaries.
3. Simulate an invalid detail response on new save; confirm no entry appears. Block provider access and inspect previously saved metadata and poster fallback.

### Acceptance criteria

- [ ] Search-to-save produces one owned authoritative local snapshot with correct defaults and visible provenance, then opens detail.
- [ ] Repeat saves open the existing unchanged entry without networking; duplicate races cannot persist multiple rows or expose integrity tracebacks.
- [ ] Different owners retain independent entries; full-page access is owner-scoped, including staff.
- [ ] Saved list/detail work without provider requests; failed new saves leave no partial entry.
- [ ] Migrations, phase tests, accumulated checks, CSS build, and manual scenarios pass with results recorded.

---

## Phase 3: Personal editing and library navigation

**User stories**: 9–14, 17; extends outage independence in 7.

**Review status**: implemented and awaiting user browser verification; not yet declared complete or committed. All three selected TDD behaviors failed on assertions before implementation and passed afterward. Actual verification: 226 full-suite pytest tests pass (64 new Phase 3 tests), with one existing Windows pytest-cache warning; the separate 7-method console suite, Django system checks, migration consistency, Ruff lint/format (52 files), and production CSS build pass. Applied personal-field and database-constraint migrations locally; a migration test verifies existing snapshot preservation and personal defaults. README records exact browser scenarios, including validation, independent progress, 21-match pagination, ownership, CSRF, and provider outages. Phase 4 has not started.

### What to build

Add personal fields and suitable constraints with a usable edit form: rating, plain-text notes, five statuses, and independent season/episode bookmark with explicit clearing. Migrate existing entries to the agreed defaults. Share validation for later API reuse. Extend the local library with combined search, status filtering, sorting and retained pagination state. Keep conventional forms and full-page responses functional; all behavior uses local data.

### Automated tests

- Rating accepts blank/1/10 and rejects 0/11/fractions; notes accept blank/5,000 characters and reject 5,001 while preserving line breaks and escaping HTML-looking content. Invalid submissions leave the saved record unchanged.
- Exercise all five statuses and reject invalid values. Bookmark accepts absent pairs, S0 E1, and ordinary pairs; rejects negative/fractional season, zero/fractional episode, and partial pairs. Verify suitable database numeric/pair constraints.
- Parameterize independence across statuses: save/correct/clear never changes status; status changes never mutate bookmarks. Replay Completed correction, Paused correction, Planned rewatch, and explicit clear from the approved prototype.
- Combined case-insensitive title search/status/sort remain owner-scoped. Test normalization, all sorts, Unrated last, deterministic ties, >20 matches, page selection retention, malformed pages, empty library versus no matches.
- Enforce owner/provider-field rejection, anonymous access, foreign-entry edit 404, POST/CSRF rules, and zero provider calls for edits and query controls.

### Manual verification scenarios

1. Rate and annotate an entry, change each status, and try validation boundaries. Save S0 E1, complete and correct a bookmark, return to Planned, then explicitly clear; confirm independence after each action.
2. With provider requests blocked, edit and browse 21+ owned entries. Combine title search, each status, and each sort; navigate pages and verify controls persist and Unrated sorts last. Check distinct empty states.
3. Try editing another account's entry and submitting owner/provider fields; confirm no stored changes.

### Acceptance criteria

- [ ] Valid personal edits persist; invalid edits return actionable field errors and preserve stored values.
- [ ] All rating, note, status, and bookmark boundaries match the PRD through shared rules and appropriate database constraints.
- [ ] Status/bookmark independence matches the selected prototype policy, including Completed corrections and Planned rewatches.
- [ ] Combined local controls, normalized defaults, stable sorting and 20-entry pagination preserve privacy and query state without provider calls.
- [ ] Migrations, phase tests, accumulated checks, CSS build, and manual scenarios pass with results recorded.

---

## Phase 4: Refresh, deletion, and HTMX interactions

**User stories**: 8, 15, 18; extends 3, 4, 7, 14, 17 and session behavior in 2.

### What to build

Add explicit protected POST refresh using the existing detail client and a shared refresh operation. Validate a complete replacement snapshot before applying it; preserve personal state and other owners' snapshots. Add a deletion confirmation naming the show and the personal data lost; only confirmed POST removes it. Enhance the already-working discovery and library query forms with locally served HTMX and shared fragments, visible loading/feedback, retained controls, and ordinary submission fallback. Keep personal edits, refresh and delete as conventional flows to bound this session.

### Automated tests

- Successful refresh changes only provider snapshot fields, retrieval time, and appropriate local update time; creation time and personal fields remain. Other owners' entries remain unchanged.
- Every detail-client failure, including provider 404 and ID mismatch, preserves the entire old snapshot, successful timestamp, and personal values. Verify a refresh cannot overwrite a concurrent personal edit or resurrect an entry deleted while HTTP was in flight.
- Confirmation GET and cancel preserve entries; POST deletes only the owned entry. Re-save creates fresh defaults. Test anonymous/foreign/staff ownership, POST-only refresh, delete protection, and CSRF.
- Full and HTMX discovery/library responses show equivalent results/query state; partial responses contain the intended fragment, feedback, and empty states. Expired HTMX authentication triggers navigation to login. Save indicators remain accurate after save/delete.
- Discovery HTMX failures retain the query. Local HTMX controls and deletion make zero provider calls. Shared throttle covers discovery, save, and refresh together.

### Manual verification scenarios

1. Refresh a show with controlled changed metadata, then with timeout/429/removal/malformed data. Compare snapshot/timestamps and personal values; verify the second owner's copy is unchanged.
2. Open and cancel deletion, then confirm it; save the show again and inspect fresh defaults. Repeat deletion while the provider is unavailable.
3. Use discovery and library controls with HTMX enabled and disabled. Inspect loading/error feedback and pagination state. Expire the session before a fragment request and confirm a full login navigation.

### Acceptance criteria

- [ ] Refresh replaces only validated provider metadata; every failure preserves prior data and never changes personal fields or another owner's copy.
- [ ] Confirmation explains permanent loss; GET/cancel do nothing, protected POST deletes, and re-save starts fresh.
- [ ] Discovery/library interactions work with and without HTMX, retaining normalized controls and clear feedback.
- [ ] Expired fragment sessions navigate to login; every new action enforces ownership, method, and CSRF rules.
- [ ] Phase tests, accumulated checks, CSS build, and manual scenarios pass with results recorded.

---

## Phase 5: Private REST API reads, creation, and updates

**User stories**: 16, 17; applies 5–7, 9–14.

### What to build

Introduce DRF session-authenticated list/retrieve/create/PUT/PATCH endpoints over existing entries. Reuse owner-scoped query controls, authoritative save operations, and personal validation. Return local metadata, personal state, and provenance without other users' account information. Paginate lists at 20 with pagination information. Document session cookies/CSRF, filters/sorts, accepted inputs, duplicate status codes, and PUT/PATCH semantics. Demonstrate API writes immediately on existing website pages; do not create a parallel UI or persistence model.

### Automated tests

- Anonymous API requests return a structured DRF authentication error rather than login HTML; owned list/retrieve are 200, foreign/missing retrieve/update are 404, and staff remain owner-scoped. List query normalization, ordering, null ratings, and pagination match the website.
- Create from ID returns 201 with defaults; duplicates return 200 unchanged without HTTP. Reuse race-protection tests and add endpoint coverage. Owner/provider/personal overrides on create and arbitrary URLs are rejected; provider failures use the specified structured status mapping with no partial record.
- PUT/PATCH update personal fields only and reject owner/provider fields. Exercise the same boundaries as the website, including boolean/fractional/non-integer JSON where inappropriate. Test documented PUT completeness and PATCH merged-pair validation; explicit two-null clearing succeeds and one-null partial clearing fails.
- Confirm provenance in representations, no credentials/other-owner information, local reads/edits make no HTTP calls, invalid writes preserve state, and unsafe session-authenticated requests fail without valid CSRF tokens. Use a real session client with CSRF enforcement, not only forced API authentication.

### Manual verification scenarios

1. Sign in through the website, use the browsable API/session client with CSRF, list/filter/page entries, retrieve one, and try another owner's ID. Repeat as ordinary staff and anonymously.
2. Create from TVmaze ID; repeat during simulated outage and inspect 201/200 behavior. Attempt owner/provider overrides and an invalid ID.
3. Change rating/notes/status/bookmark using PATCH and complete personal state using PUT. Try a partial bookmark, then clear both fields. Reload the website to verify the same saved values.

### Acceptance criteria

- [ ] List/retrieve expose only owned local entries with matching query behavior, 20-entry pagination, and provenance.
- [ ] API create uses authoritative metadata and server-owned defaults, returns 201/200 correctly, and preserves duplicate entries without networking.
- [ ] PUT/PATCH obey documented personal-only semantics, shared validation, independent bookmarks/status, and structured errors.
- [ ] Session authentication, owner-scoped 404s, CSRF, and provider-error mappings are covered; local API reads/edits work during outage.
- [ ] Phase tests, accumulated checks, CSS build, and manual scenarios pass with results recorded.

---

## Phase 6: REST API refresh/deletion and complete workflow verification

**User stories**: 16, 17; applies 8, 15, 18. Final verification spans all stories 1–18.

### What to build

Complete the API with explicit POST refresh and immediate authorized DELETE, reusing established operations. Document their success/error contracts and complete the demonstration instructions. Verify complete website/API workflows, isolation, outage handling, and clean setup. This session adds working refresh/deletion endpoints; final checks validate accumulated work rather than postponing earlier tests or access control.

### Automated tests

- Refresh returns 200 with updated provider data and unchanged personal fields/creation time; verify independent snapshots and no stale overwrite of concurrent personal edits. Failed refresh preserves the prior successful timestamp and every saved field.
- Assert 504 timeout, retryable 503 rate-limit/wait guidance, 502 connection/other upstream/invalid payload/removal, and structured errors without provider HTML or secrets. Contrast provider-404 creation 400 with refresh 502.
- DELETE returns 204 and permanently removes only the owned entry; foreign/missing delete/refresh return 404, including staff sessions. Unsupported methods do not mutate. Enforce session CSRF and anonymous JSON errors. Re-create after deletion starts fresh.
- Add a compact cross-surface test: website save, API personal edit, website display, API refresh, website display, API delete, website absence. With HTTP mocked to fail, verify website/API local reads, query controls, personal edits and deletion still work; duplicate create avoids HTTP.
- Run all accumulated application tests and existing console tests, migration checks, Ruff checks, Django system checks, production CSS build, and verify dependency setup from the committed uv lockfile.

### Manual verification scenarios

1. Demonstrate discovery → save → edit → independent bookmark correction → library query → API update → website reload. Confirm attribution, accessible feedback, and failed-poster fallback.
2. With two ordinary users and a staff session, verify private lists and cross-owner detail/edit/refresh/delete rejection on website/API. Confirm expired HTMX login handling and missing-CSRF rejection.
3. Refresh through API successfully, then simulate timeout, rate limit, removal and malformed response. Verify status/wait guidance and unchanged last good data on the website.
4. Delete through API, observe website absence, then save afresh. Separately demonstrate website cancel/confirm. With provider access unavailable, show local list/detail/query/edit/delete remain usable.
5. Follow documented locked dependency setup, migrations, asset build, test and run commands in a clean local setup; record outputs and any environmental limitations without claiming unrun checks passed.

### Acceptance criteria

- [ ] Owned API refresh returns 200 and obeys atomic preservation rules and the complete structured error contract.
- [ ] Owned API deletion returns 204 without a separate confirmation; unauthorized access and missing CSRF never mutate data.
- [ ] Website and API expose consistent data and rules, with two-user/staff isolation and demonstrated provider independence.
- [ ] All PRD stories and acceptance criteria are demonstrated or tied to meaningful deterministic tests; no application feature remains deferred.
- [ ] Locked dependency setup, full pytest suite, separate console verification tests, Ruff lint/format, Django checks, migration consistency, applied migrations, and production CSS build pass with actual results recorded.
- [ ] Manual scenarios and remaining limitations are recorded before implementation is declared complete.

## Workload and coverage review

- Six phases were explicitly requested and approved after the initial twelve-phase proposal. Each has one session boundary and reuses prior infrastructure: phase 1 stops at read-only discovery, phase 2 at save/local browsing, phase 3 at local personal management, phase 4 completes the website, phase 5 exposes existing operations through DRF, and phase 6 adds the final API actions and end-to-end verification.
- Phases 3 and 4 are the broadest sessions. Keep forms and styling conventional, use one personal-edit flow, enhance only discovery/library controls with HTMX, and reuse the detail client for refresh. Do not expand either with inline editing, extra filters, episode lookup, or new architecture.
- Story coverage: 1–2 → phase 1 (expiry enhanced in 4); 3–4 → phases 1–2 and 4; 5–7 → phase 2, API parity in 5; 8 → phases 4 and 6; 9–14 → phase 3, API parity in 5 and HTMX query behavior in 4; 15 → phases 4 and 6; 16 → phases 5–6; 17 → every applicable phase; 18 → phases 1, 2, 4–6.
- PRD acceptance coverage: 1 → phase 1; 2 → all newly introduced access paths; 3–4 → phases 1 and 4; 5–7 → phases 2 and 5; 8 → phases 2–6; 9 → phases 4 and 6; 10–12 → phases 3 and 5; 13 → phases 3–5; 14 → phases 4 and 6; 15 → phases 5–6; 16 → phases 1–2 and 5; 17 → every phase; 18 → per-phase checks and final phase 6 verification.
- Tests and manual scenarios above are planned, not executed. No implementation, dependency changes, new live API research, or browser verification was performed while creating this plan.

# ShowVault Product Requirements Document

Status: requirements synthesized from the completed interview. Application implementation is not authorized by this document-creation task.

## Problem Statement

TV viewers need a private place to discover shows and remember what they intend to watch, what they have finished, where they stopped, and what they thought. Provider outages must not prevent them from viewing or editing shows they already saved. Users also need programmatic access to their own saved entries without exposing anyone else's library.

## Solution

ShowVault is an authenticated Django website and Django REST Framework API backed by SQLite. Users search TVmaze, save shows with local metadata snapshots, and maintain private ratings, notes, watch statuses, and last-watched season/episode bookmarks. Local library searching, filtering, sorting, pagination, and personal edits work independently of TVmaze. Users explicitly request metadata refreshes.

### Assignment requirements coverage

| Requirement | Product behavior |
| --- | --- |
| Search an external API | Authenticated, server-side TVmaze show search |
| Save selected items locally | Per-user SQLite entries with provider IDs and display metadata snapshots |
| Personal annotations and progress | Optional rating and notes, five statuses, manual season/episode bookmark |
| Private library management | Local title search, status filter, three sort orders, 20-entry pagination |
| Own REST API | Authenticated list, create, retrieve, update, delete, and explicit refresh |
| Authentication and ownership | Owner-scoped website, HTMX, and API operations; cross-owner detail requests return 404 |
| External failure handling | Timeouts, HTTP errors, rate limiting, empty results, malformed responses, and missing optional data handled without losing saved data |
| Required technology | Django, DRF, SQLite, uv, Ruff, Tailwind CSS/DaisyUI through django-tailwind-cli, HTMX, pytest/pytest-django |

## User Stories

1. As an administrator, I want to create ordinary accounts in Django admin, so that authorized users can sign in without public registration.
2. As a user, I want to sign in and sign out, so that my personal library remains private.
3. As a user, I want to submit a show-title search to TVmaze, so that I can discover shows to save.
4. As a user, I want recognizable search results with titles, premiere years, summaries, posters, and saved indicators, so that I can select the intended show.
5. As a user, I want to save a show immediately as Planned, so that collecting shows takes few steps.
6. As a user, I want a repeated save to open my existing entry without changes, so that I do not create duplicates or lose personal information.
7. As a user, I want saved text metadata available locally, so that provider outages do not prevent me from using my library.
8. As a user, I want to refresh a saved show's provider details explicitly, so that I can update stale information without changing my personal fields.
9. As a user, I want to assign or clear a whole-number personal rating from 1 to 10, so that I can record my opinion.
10. As a user, I want optional private plain-text notes, so that I can retain reviews and reminders safely.
11. As a user, I want Planned, Watching, Paused, Completed, and Dropped statuses, so that I can describe my viewing intentions accurately.
12. As a user, I want a last-finished season/episode bookmark independent of status, so that corrections and status changes do not erase or reinterpret my progress.
13. As a user, I want to clear a bookmark explicitly, so that I can restart tracking when appropriate.
14. As a user, I want to search my saved titles, filter by status, sort, and page through results, so that I can find entries in a growing library.
15. As a user, I want to confirm permanent deletion on the website, so that I understand which personal information will be lost.
16. As an API client acting as a signed-in user, I want CRUD and refresh operations, so that I can manage the same private entries programmatically.
17. As a user, I want other accounts blocked from accessing or changing my entries, so that private information remains isolated.
18. As a user, I want clear empty-result and service-failure messages with my search retained, so that I know whether to change the query or retry later.

## Implementation Decisions

### Stack and structure

- Use Django and Django REST Framework with SQLite, uv dependency management and lockfile, Ruff linting/formatting, and pytest with pytest-django.
- Follow the previous ATS project's conventional Django models, forms, views, templates, authentication, and admin approach. Use a configuration package and one shows application rather than a larger service architecture.
- Use Tailwind CSS and DaisyUI through django-tailwind-cli, Django-rendered HTMX fragments, locally served HTMX, and a shared base template. No separate frontend build framework or Node toolchain is required.
- Keep TVmaze HTTP behavior in a small client component. Share save/refresh business operations and personal-field validation rules across website and API; do not duplicate policy in unrelated views.
- Preserve standard Django CSRF protection. State-changing website actions use protected POST requests; GET never saves, refreshes, logs out, or deletes.
- Existing research and console verification are reference material, not an implemented Django application. Resolve compatible dependency versions during implementation; the existing project and ATS use Python 3.14.

### Authentication and ownership

- Administrators create ordinary active Django users through Django admin. Staff status is not required for ShowVault use. Public signup is excluded.
- Require login for discovery, all library pages/actions, HTMX endpoints, and all API endpoints. Browser sign-in uses Django sessions; sign-out uses CSRF-protected POST.
- DRF uses session authentication and authenticated-user permissions, including CSRF enforcement for unsafe authenticated requests. No token or JWT authentication.
- Scope all entry queries to the current user before retrieval, mutation, refresh, or deletion. A missing entry and another user's entry both produce 404. HTML and JSON response formats may differ, but isolation must not.
- Set ownership from the authenticated request on creation. Reject attempts to set or change owner through forms or JSON. Staff and superusers using the ordinary website/API are still restricted to their own entries.
- Django admin is a privileged administrative surface, not a private-library browsing shortcut. Ordinary users cannot access it. Account administration does not require exposing entries in admin.
- Unauthenticated full-page website requests redirect to login. HTMX authentication expiry must lead to login rather than inserting a login page into a results fragment. Unauthenticated API requests return an appropriate DRF authentication error, not an HTML login redirect; session authentication may use 403.

### Local entry and metadata model

- Store a separate snapshot for each user's saved show, not a shared show catalog. Refreshing one entry cannot update another user's snapshot.
- Enforce a database uniqueness constraint on owner plus TVmaze show ID. Distinct users may save the same show independently. Concurrent duplicate requests must not leave duplicate rows or an unhandled integrity error.
- Each entry stores its local identifier, owner, positive TVmaze show ID, provider source link, title, plain-text summary, genres, language, premiere/end dates, provider show status, poster URL, successful retrieval timestamp, personal rating, notes, watch status, bookmark, and local creation/update timestamps.
- Keep provider show status separate from the user's watch status. Provider ratings are not needed in this version and must never be confused with a personal rating.
- Store attribution/provenance identifying TVmaze, the source show link, CC BY-SA 4.0 license link, and the fact that summaries were converted to plain text. Present provenance on the website and in API entry representations.
- Null or absent optional provider fields render useful placeholders. Missing posters use a locally served placeholder, including when a stored image URL fails to load.
- Store poster URLs only; do not download images. Text metadata and personal fields remain available during outages, but posters may be unavailable.
- Convert external summary HTML to plain text and escape output. Do not render arbitrary provider HTML or user notes as trusted markup.
- Initial save and refresh use server-fetched metadata from the official provider. Clients cannot supply replacement provider metadata or arbitrary fetch URLs.
- Refresh replaces the provider snapshot only after the entire required response has been validated. A failed refresh leaves the prior snapshot and successful retrieval timestamp intact. Personal fields and creation time are never changed by refresh.

### Personal fields and validation

| Field | Rules |
| --- | --- |
| Rating | Optional integer from 1 through 10; blank/null means Unrated; zero, fractional values, and out-of-range values are invalid |
| Notes | Optional plain text, at most 5,000 characters; preserve line breaks; render escaped; blank is allowed |
| Watch status | Exactly Planned, Watching, Paused, Completed, or Dropped; new entries default to Planned |
| Last season finished | Optional whole number of 0 or higher; 0 represents specials |
| Last episode finished | Optional whole number of 1 or higher |
| Bookmark pair | Both values present or both absent; reject a partially filled pair; do not verify existence against TVmaze |
| External show ID | Positive integer; required for creation; server validates a new show's provider response |
| Ownership/provider fields | Server-controlled; not writable through ordinary personal updates |

- Status and bookmark are independent under all operations. Saving/correcting/clearing a bookmark never changes status. Changing status never changes or clears the bookmark.
- Completed means the user considers their viewing finished; no finale detection or episode-total calculation is performed. Every status may have a blank or valid bookmark. Ratings and notes are permitted in every status.
- Clearing a bookmark is explicit. Rewatching reuses the same entry; there is no separate watch history.
- Apply consistent validation through Django forms and DRF serializers, with database constraints for ownership uniqueness and suitable numeric/pair invariants. Invalid writes preserve existing saved values and return actionable field errors.

### Website workflows

- After sign-in, users reach their private library with clear navigation to TVmaze discovery. Local title search and external discovery are visibly distinct.
- Discovery uses a submitted GET search form, not search-as-you-type. Trim input and reject an empty query before making a provider request. Preserve the submitted phrase after empty results or failure.
- Display TVmaze relevance order, with show title, premiere year when known, poster or placeholder, summary, and a saved indicator. Do not imply the console script's five-result display limit is an application requirement; render the finite search results returned by the provider without inventing external pagination.
- HTMX updates discovery results without a full reload; ordinary form submission remains usable. Provide visible loading and result/error feedback.
- Save is a POST action. For a new show, retrieve authoritative detail data using its TVmaze ID, then create an entry as Planned with no rating, blank notes, and no bookmark. Open its detail page for subsequent editing.
- For an already-saved show, open the existing entry unchanged and do not contact TVmaze. This behavior also applies when TVmaze is unavailable.
- The detail page displays local metadata, source attribution and retrieval time, personal fields, and explicit edit, refresh, and delete actions.
- The library supports case-insensitive title substring search, one watch-status filter, and sorts for recently saved (default), title A–Z, and personal rating highest first. Rating sorting places Unrated last. Use deterministic tie-breaking to prevent unstable pagination.
- Paginate at 20 entries. Preserve normalized search, filter, and sort selections across pages and HTMX updates. Follow ATS conventions by normalizing invalid filter/sort choices to defaults. Empty libraries and no local matches have distinct useful messages.
- Website deletion uses a confirmation page naming the show and explaining that notes, rating, status, and bookmark will be permanently lost. Only a subsequent protected POST deletes. Cancel leaves the entry untouched.
- Saving a deleted show again creates a fresh Planned entry with no prior annotations. No trash or restore exists.

### REST API contract

The following resource operations are required; final URL spelling is an implementation detail.

| Operation | Input and behavior | Successful outcome |
| --- | --- | --- |
| List | Current user's entries only; same title search, status filter, sort options and page size as website | 200 with paginated entries and pagination information |
| Create | TVmaze show ID only; server fetches provider details for a new entry; server assigns owner and personal defaults | 201 for new entry; 200 with unchanged existing entry for duplicate |
| Retrieve | Owner-scoped local entry ID | 200 with local snapshot, personal fields, and provenance |
| Update | PUT/PATCH for personal rating, notes, status, and bookmark only; apply the same field and pair validation | 200 with updated entry |
| Delete | Owner-scoped local entry ID; no separate API confirmation | 204; permanent removal |
| Refresh | Explicit authenticated POST action on an owned entry; no client-supplied metadata | 200 with refreshed entry |

- Duplicate create checks ownership-scoped local data before networking and never applies personal updates. API callers edit the existing resource separately.
- Entry representations expose only the current user's data. Do not expose credentials or other users' account information. Provider provenance fields are readable but not writable.
- For PATCH, validate the resulting bookmark pair against existing values; clearing requires both values to become null. PUT follows documented serializer semantics and the same invariants.
- Use structured validation errors (400), owner-scoped not-found errors (404), and structured provider-failure errors. Do not return raw tracebacks, provider HTML, or secrets.
- Map upstream timeouts to 504, upstream rate limiting to a retryable 503 with wait guidance, and other invalid/failed upstream responses to 502. A provider detail 404 during creation produces a useful invalid-show-ID error (400); during refresh it reports provider unavailability/removal (502) and preserves the snapshot. These are error-contract details derived from the agreed graceful-failure policy.
- Session-authenticated writes require CSRF protection, including the browsable API. API clients must manage session cookies and CSRF tokens; external token-client convenience is outside this version.

### TVmaze integration and failure handling

- Use the official public show-search and show-detail endpoints server-side. No TVmaze API key or per-user provider account is required according to the supplied research.
- Send URL-encoded query parameters and an identifying User-Agent. Use a 10-second connection/read timeout; this is not a strict total-request deadline.
- No automatic retry. Users explicitly retry search/save/refresh. Honor rate-limit wait guidance where supplied and avoid rapid repeated requests; enforce a small shared request throttle at the client boundary for the local deployment rather than letting individual views independently flood the provider.
- Validate HTTP status, JSON decoding, expected response shape, identity, and required display fields before persistence. Detail IDs must match the requested ID. A new save or refresh is all-or-nothing.
- Treat an empty search list as a normal no-matches result, distinct from service failure. Empty/malformed detail responses are errors. A successful empty search must not produce a failure banner.
- Catch timeouts, connection failures, HTTP errors including 404/429/5xx, invalid JSON, and unexpected/malformed data. Give users clear retry or query-change guidance without an unhandled exception.
- Handle absent optional metadata with placeholders; do not reject otherwise valid shows solely for missing poster, dates, genres, language, or summary.
- On a new-save failure, create no partial entry. On refresh failure, change no saved provider or personal values. Existing local listing, retrieval, personal editing, and deletion must make no provider request.
- Research documents provider caching and rate limits but does not establish an uptime guarantee. Do not add automatic synchronization, catalog mirroring, or background refresh infrastructure.

### Acceptance criteria and verification

Acceptance is based on observable behavior, not merely the existence of components.

1. An administrator can create two ordinary accounts; each can sign in without staff privileges, sign out through POST, and see only its own library.
2. Unauthenticated full-page, HTMX, and API access is blocked appropriately. Cross-owner retrieve, edit, refresh, and delete requests return 404 and change nothing, including for staff using ordinary application endpoints.
3. A nonblank discovery search sends a server-side encoded TVmaze request and displays ordered results with missing-field fallbacks. A blank search makes no provider request.
4. Empty results show a normal no-matches state. Timeout, connection failure, 429, other HTTP failure, invalid JSON, and invalid response shape produce useful failure feedback and retain the query.
5. Selecting a new show creates one owned local snapshot with Planned, Unrated, blank notes, and no bookmark, then opens the detail page. Required invalid provider data creates no entry.
6. Repeated website or API saves return the same entry unchanged, including during an outage; concurrent duplicate creation cannot persist two entries. API status is 201 for new entries and 200 for duplicates.
7. A second user can save the same provider show with an independent snapshot and personal fields. Refreshing one does not change the other.
8. With provider requests mocked to fail, saved lists/details, local query controls, personal edits, and deletion still work. A failed poster request uses the local placeholder.
9. A successful refresh updates only the requesting entry's provider snapshot and retrieval timestamp. Every tested refresh failure preserves the last good snapshot, timestamp, and personal fields.
10. Ratings accept blank and whole numbers 1–10; reject 0, 11, and fractional values. Notes accept 5,000 characters and reject 5,001. HTML-looking notes and provider summaries cannot execute markup.
11. All five statuses are accepted; invalid statuses are rejected on writes. No status change mutates progress, and no bookmark change mutates status.
12. Bookmarks accept both blank, S0 E1, and ordinary nonnegative-season/positive-episode pairs. Negative, fractional, zero-episode, and partial pairs are rejected consistently through website and API. Corrections to Completed entries leave Completed unchanged, matching the selected independent prototype policy.
13. Local title search, each status filter, and all three sort modes work only on owned entries. Unrated entries sort last by rating; more than 20 results paginate without losing query selections or destabilizing tied ordering.
14. Website delete confirmation identifies the show; GET and cancel do not delete. Confirmed POST and authorized API DELETE remove the entry permanently. A later save starts fresh.
15. API list/create/retrieve/PUT/PATCH/DELETE/refresh behavior matches the contract, rejects owner/provider-field changes, validates personal fields consistently, and enforces CSRF for session-authenticated writes.
16. The website presents attribution and API entries contain provenance. Missing optional provider fields do not break rendering or serialization.
17. Meaningful pytest/pytest-django coverage uses mocked provider responses for deterministic success and failure cases. Retain the existing console verification as separate evidence; tests do not depend on live TVmaze availability.
18. Before declaring implementation complete, dependency setup from the uv lockfile, pytest, Ruff lint and format checks, Django system checks, migration consistency checks, and the Tailwind production CSS build pass. Manually demonstrate search-to-save, editing, API changes visible on the website, two-user isolation, and graceful provider failure.

## Out of Scope

- Application implementation in this PRD-writing task, and a phased implementation plan.
- Public registration, email verification, self-service password recovery, social login, tokens, and JWT authentication. Administrators handle account/password support through Django admin.
- Public profiles, shared lists, reviews visible to other users, collaboration, and social features.
- Multiple providers, movie/book/game tracking, a shared show catalog, bulk imports, and client-supplied provider snapshots.
- Individual episode checklists, episode synchronization, automatic completion, episode existence checks, next-episode calculation, viewing history, and separate rewatch entries.
- Automatic metadata refresh, background jobs, automatic request retries, and provider uptime guarantees.
- Local poster downloads, Markdown/rich-text notes, fractional ratings, trash/restore, and advanced library filters/sorts beyond the selected controls.
- Separate frontend application, production hosting/deployment, and infrastructure intended for a large multi-server service.

## Further Notes

- Decision references: the completed interview, the existing TVmaze provider research and console verification script/tests, and the watch-progress logic prototype. The user explicitly selected the independent policy after the prototype was supplied, then selected the five-status set. The prototype's assisted default and exploratory wording are not requirements; this PRD records the final choices.
- Prototype code remains throwaway and is not production architecture. Implement approved behavior in the required Django stack rather than promoting its inline JavaScript into application business rules.
- The research describes TVmaze data as CC BY-SA and calls for attribution, source/license links, and disclosure of transformations. Preserve these on reused data and review the supplied primary-source references during integration; this does not assign that license to users' independently authored notes or automatically determine the application source-code license.
- Research was already performed and live console checks were recorded before this PRD. This document does not claim new live verification, application tests, or measured provider availability.
- No interview decisions remain blocked. Additional implementation details should follow these requirements and the ATS conventions without expanding product scope.

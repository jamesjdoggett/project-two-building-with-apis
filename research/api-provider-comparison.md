# Public API comparison for Project #2

Research date: **November 14, 2026**. Scope: an authenticated Django website and Django REST Framework API, SQLite persistence, uv dependency management, and Ruff. This is research and a provider recommendation; no application has been implemented.

## Recommendation

Choose **TVmaze** for the easiest development and classroom demonstration. Choose **Open Library** for a reading tracker, or **TMDB** for a richer movie watchlist. These three offer clear search-to-selection workflows and useful metadata without requiring every application user to connect an external account. The ranking below is an engineering judgment based on the documented constraints, not a measured uptime ranking.

| Rank | Provider | Possible application | Why practical | Main tradeoff |
| --- | --- | --- | --- | --- |
| 1 | TVmaze | Personal TV watchlist: save shows, notes, personal rating, planned/watching/finished status | No public-search credentials; fuzzy search; show and episode identifiers | Attribution and ShareAlike obligations for reused data |
| 2 | Open Library | Reading journal: save books, review, rate, track reading status | No key for public reads; title/author search; aligns with educational use | Work-versus-edition modeling and incomplete metadata |
| 3 | TMDB | Movie diary: save films, write reviews, record rating and date watched | Strong movie search and detailed metadata; one server-side credential | Key setup, required branding, and unresolved full storage/redistribution terms |

Use one provider initially. Combining five media categories would multiply identity, data-normalization, and licensing work without improving the required CRUD demonstration.

## Comparison at a glance

“Free” describes a suitable classroom/noncommercial use case, not unrestricted rights or unlimited traffic. Authentication below refers to **provider access**; all choices still require the project's own Django user authentication and per-user authorization.

| Category / provider | Public catalog authentication | Verified free access / limits | Search and detail workflow | Assessment |
| --- | --- | --- | --- | --- |
| Television — TVmaze | No key for public endpoints | At least 20 calls/10 seconds/IP; may tighten temporarily | `/search/shows?q=…`, `/shows/{id}`, episodes | Easiest overall. [Docs](https://www.tvmaze.com/api) |
| Books — Open Library | No key in public-read workflow; asks developers to register applications | 1 request/second unidentified; 3 identified | `/search.json`, work/edition JSON | Best book option for this project. [Usage](https://openlibrary.org/developers/api) |
| Movies / TV — TMDB | Account and API key or read access Bearer token | Noncommercial free with attribution; approximate abuse ceiling around 40 requests/second, changeable | `/3/search/movie` or `/3/search/tv`, detail by ID | Best rich movie option. [Authentication](https://developer.themoviedb.org/docs/authentication-application), [limits](https://developer.themoviedb.org/docs/rate-limiting), [FAQ](https://developer.themoviedb.org/docs/faq) |
| Movies / TV — OMDb | Emailed API key | Free key: 1,000 requests/day | `?s=…`, then `?i=IMDb_ID` | Simple runner-up; smaller quota. [Keys](https://www.omdbapi.com/apikey.aspx), [reference](https://www.omdbapi.com/) |
| Games — RAWG | API key on every request | Pricing says noncommercial, 20,000 requests/month | `/api/games?search=…`, details | Appealing catalog; terms conflict and redistribution restriction weaken fit. [Official API page](https://rawg.io/apidocs) |
| Games — IGDB | Twitch developer account, 2FA, client ID/secret and OAuth app token | Noncommercial free; 4 requests/second, up to 8 concurrent requests | POST `/v4/games` with search/fields/filter body | Best games alternative if token handling is acceptable. [Docs](https://api-docs.igdb.com/) |
| Music — MusicBrainz | No key for public metadata; meaningful User-Agent required | Noncommercial free; maximum 1 call/second/application | `/ws/2/release-group?query=…&fmt=json`, entity lookup | Best open music metadata option; more modeling work. [API](https://musicbrainz.org/doc/MusicBrainz_API), [search](https://musicbrainz.org/doc/MusicBrainz_API/Search) |
| Books — Google Books | API key or OAuth token identifies public requests; user OAuth for private Google data | Numeric daily allowance not verified in public docs reviewed; inspect project quota before choosing | `/books/v1/volumes?q=…`, `/volumes/{id}` | Useful alternative, but more policy and quota uncertainty. [Guide](https://developers.google.com/books/docs/v1/using) |

## Provider findings

### TVmaze — recommended easiest

Public REST endpoints return JSON without registration. Name search tolerates small typos and returns full show information; `/shows/{id}/episodes`, seasons, cast, people search and schedules support later expansion. Responses are cached upstream for 60 minutes. Handle HTTP 429 with backoff; set an identifying User-Agent. Image hotlinking and caching are documented. Data use is CC BY-SA. These points and the rate limit above come from [TVmaze's API documentation](https://www.tvmaze.com/api).

A successfully retrieved [official live show response](https://api.tvmaze.com/shows/1) contained `id`, `name`, `url`, `genres`, language, status, premiere date, runtime, average rating, network, external IDs, images, `updated`, and an HTML summary. Treat nullable/missing fields defensively and sanitize or strip external HTML. This is one successful read, not an availability measurement.

The API links to [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/): retain attribution and license information, indicate changes, and apply ShareAlike where adapted material is shared. This does not automatically determine the license of all application source code or users' independently authored notes. For the project's REST responses, keep provider attribution/provenance alongside reused fields rather than dropping it from JSON.

### Open Library — recommended books

The [current usage guidelines](https://openlibrary.org/developers/api) prioritize education, research, and human book discovery. They ask for application registration, identification with application/contact information, and response caching. Bulk harvesting and using the API as high-traffic commercial infrastructure are discouraged; violations can cause blocking. This makes a small human-driven class project a good fit, with search throttling.

The [Search API](https://openlibrary.org/dev/docs/api/search) supports free-text, title and author queries, pagination, sorting and explicit field selection. Useful fields include work key, title, author names/keys, first publication year and cover ID. Search normally groups editions into works; its schema is not guaranteed stable. Choose work-level saving for a simple journal; choose a specific edition only if page-count progress is essential. Work/edition and author JSON are also indexed in the developer documentation.

The [Covers API](https://openlibrary.org/dev/docs/api/covers) supports cover IDs, OLIDs and ISBNs, with small/medium/large images. Public pages should reference its cover URLs; unavailable covers need a placeholder. The [licensing statement](https://openlibrary.org/developers/licensing) asserts no new Internet Archive rights but explicitly acknowledges possible existing rights. Do not describe all covers, descriptions or full books as public domain. Saving selected bibliographic records is consistent with the caching guidance; wholesale republication or ebook distribution is a different use case.

### TMDB — recommended movies, with a terms caveat

An application [read access Bearer token or API key](https://developer.themoviedb.org/docs/authentication-application) suffices for public metadata: users need no TMDB account for a locally managed watchlist. [Movie search](https://developer.themoviedb.org/reference/search-movie) matches original, translated and alternative titles and supports pagination/year/language filters. [TV search](https://developer.themoviedb.org/reference/search-tv) and [movie details](https://developer.themoviedb.org/reference/movie-details) are separate endpoints. The [official OpenAPI specification](https://developer.themoviedb.org/openapi/tmdb-api.json) documents IDs, titles/names, overview, release/air dates, genres, runtime, poster/backdrop paths and vote statistics. Use `(media_type, id)` as identity when mixing movies and TV. [Image documentation](https://developer.themoviedb.org/docs/image-basics) explains configuration, image sizes and path construction.

The [FAQ](https://developer.themoviedb.org/docs/faq) permits free noncommercial use with attribution, requires an approved logo and its specified endorsement disclaimer in About/Credits, and explicitly offers **no SLA**, linking an [official status page](https://status.themoviedb.org/). It also notes third-party image/data rights. The [rate-limit guide](https://developer.themoviedb.org/docs/rate-limiting) replaces the obsolete 40-per-10-seconds rule with a changeable anti-abuse ceiling around 40/second; respect 429 responses. No fixed monthly free quota is stated there.

**Unresolved:** the complete API terms were not accessible to this research browser. The FAQ is not a verified blanket license for permanent metadata archives or downstream REST redistribution. Before implementation, review the terms accepted with the key for selected snapshots, caching duration and JSON exposure. Keep the own REST API focused on authenticated users' saved records and annotations; do not promise a public mirror of TMDB's catalog.

### OMDb — simple movie alternative

The [main reference](https://www.omdbapi.com/) supports title search with `s`, detail by `i` (IMDb ID) or `t`, movie/series/episode filters, release year, short/full plot, pagination, and season/episode lookup. The dedicated high-resolution Poster API is patron-only; do not assume it is included with a free key. Its published content license is **CC BY-NC 4.0**, requiring attribution and noncommercial use. A film diary is straightforward, though search followed by details consumes multiple calls.

The [key page](https://www.omdbapi.com/apikey.aspx) lists 1,000 free daily requests and warns of email delivery delays, especially Yahoo/Microsoft addresses. Obtain a key early. The [official Swagger](https://www.omdbapi.com/swagger.json) verifies search/lookup authentication but does not provide a comprehensive response-field schema; exact optional metadata should be checked with an issued key. The homepage's server-upgrade changelog is maintenance evidence, not an uptime guarantee. No SLA was found in the reviewed reference.

### RAWG — easy game search, weaker policy fit

The [official API page](https://rawg.io/apidocs) requires a key, documents game search including precise/exact options, filters by platforms/dates/genres and offers game descriptions, release dates, ratings, playtime and imagery. Its current free pricing lists **20,000 monthly requests, noncommercial use, and backlinks on pages using the data**. However, the same page's terms section still describes some commercial use as free: treat this as a conflict, not permission to choose the more generous wording. It also forbids data redistribution, creating uncertainty for a project that must expose saved metadata through its own API. Ask RAWG about that scope before selecting it. An authenticated personal backlog with notes, rating, hours played and completion status is a natural idea. The detailed schema was not readable in this browser; do not treat every advertised feature as verified free-tier access. No SLA was established.

### IGDB — strongest games alternative when games are the priority

[IGDB documentation](https://api-docs.igdb.com/) specifies free noncommercial use under the Twitch agreement, a Twitch account with 2FA, confidential app registration, and a client-credentials token. Send Client-ID and Bearer headers; handle token expiry. Game queries support search, selected fields and filters; related endpoints cover platforms, genres, covers and release dates. Useful fields include ID, name, summary, release date and ratings. Direct browser calls are restricted. A game completion journal fits, but authentication and query syntax add effort. The linked [Twitch developer agreement](https://legal.twitch.com/en/legal/developer-agreement/) did not render substantive terms here; exact cache/redistribution permissions remain unverified. No uptime SLA was established.

### MusicBrainz — best music candidate for metadata

The [API guide](https://musicbrainz.org/doc/MusicBrainz_API) provides public lookup, browse and search in XML or JSON (`fmt=json`). Noncommercial use is free; no API key is required, but a meaningful User-Agent and at most one call per second are required. Public reads need no user authorization; protected submissions and private data differ. The docs acknowledge that breaking changes can occur and announce them on their blog.

The [search reference](https://musicbrainz.org/doc/MusicBrainz_API/Search) supports artists, recordings, releases and release groups with structured query fields and pagination. Use release groups for an album journal to avoid saving each regional/reissued release as a separate album. [Official examples](https://musicbrainz.org/doc/MusicBrainz_API/Examples) illustrate MBIDs, titles, artist credits, dates, country and track-related metadata. A listening journal can store albums, personal ratings, notes and listened/want-to-listen status; it need not stream music.

The [data license](https://musicbrainz.org/doc/About/Data_License) separates CC0 core metadata from CC BY-NC-SA supplementary data. Cover art comes from a separate service, so it adds another rights/dependency check. Core metadata is attractive for local persistence and REST output; do not assume community ratings/tags or artwork have the same rights. Shared server-side throttling matters even when several Django users search simultaneously. No SLA was established from these docs.

### Google Books — workable, less predictable book alternative

The [guide](https://developers.google.com/books/docs/v1/using) requires application identification by key or OAuth token for public data; private Google library operations need user OAuth. Search supports terms such as `intitle:`, `inauthor:` and `isbn:`. The [list reference](https://developers.google.com/books/docs/v1/reference/volumes/list) documents pagination, language/type filters, relevance/newest ordering and a maximum 40 results per request. The [volume resource](https://developers.google.com/books/docs/v1/reference/volumes) includes title, authors, publisher/date, description, identifiers, page count, categories, images and access information. A reading tracker can keep all personal state in SQLite rather than Google Bookshelves.

No universal numeric daily free quota was verified in the reviewed primary pages; do not rely on the frequently repeated “1,000/day” without checking the enabled project's console. [Books terms](https://developers.google.com/books/terms) restrict charging application users without permission and require infringement removals/contact information. [General API terms](https://developers.google.com/terms) restrict caching beyond permitted cache headers and redistribution in prohibited forms; public metadata is not an unrestricted permanent-copy license. Verify allowed selected-item storage before choosing it. No uptime guarantee was established.

## Other music options screened

[Apple's iTunes Search API](https://performance-partners.apple.com/search-api) has public search/lookup URLs with no documented key requirement, music/album/song filters and approximately 20 calls/minute, subject to change. Its promotional artwork/previews must promote store content and sit near a store badge; previews are not general entertainment assets. This complicates a neutral personal journal. MusicBrainz is a cleaner metadata-focused choice.

[Spotify development mode](https://developer.spotify.com/documentation/web-api/concepts/quota-modes) currently requires the app owner to have Premium and permits up to five authenticated allowlisted Spotify users. It also has changeable quota buckets; [rate limits](https://developer.spotify.com/documentation/web-api/concepts/rate-limits) use a rolling 30-second window rather than a universal published number. These account and demonstration constraints make it a poor default for a free classroom project. This is a screening exclusion, not a full evaluation of Spotify endpoint or content licensing.

## Fit with the required application

The following are proposed design boundaries, not implemented features:

1. Require Django login to search and to create/read/update/delete saved items. Provider credentials belong to the server, separate from the user's Django credentials.
2. Save a provider identifier, source link, minimal permitted display metadata and retrieval timestamp. Keep independently authored notes, personal rating and progress in user-owned SQLite records. Deduplicate each user's saved `(provider, type, external_id)`.
3. Expose the same saved-item operations through HTML pages and DRF. Filter queries by owner and enforce ownership on detail/update/delete requests. Local saved lists and editing should work when the provider is unavailable.
4. Validate ratings and progress locally; distinguish the user's rating from the provider's aggregate rating. Start with status progress (planned/in progress/finished); edition page totals or episode tracking can follow later.
5. Use server-side requests with timeouts, bounded result counts, appropriate identification and shared throttling. Handle empty results, missing images, malformed metadata, 429 and upstream failure. Cache only as permitted; preserve provenance/licensing in website and REST output. uv and Ruff do not affect provider compatibility.

For the **smallest TVmaze demonstration**, search for a show, select and save it, add a note/rating/status, show it in the personal list, update it through DRF, reload the website, and delete it. Demonstrate a second Django user cannot access the first user's saved record. Keep episode synchronization outside the initial scope.

## Reliability and verification limits

This comparison verifies documented behavior, published policies and one successful TVmaze metadata response. It does not benchmark latency, establish historical uptime, create provider accounts, validate key issuance, or exercise authenticated endpoints. A browser fetching documentation is not a service health test; fetch failures alone are not evidence of provider outages. Only TMDB's reviewed FAQ explicitly addressed an SLA, stating none is provided. For all other providers, absence of a guarantee in the reviewed sources should be read as **not verified**, not proof that no agreement exists.

Before committing to a provider, perform a small credential/search/detail check with representative titles, confirm the accepted current terms cover selected local records and own REST responses, and test a missing-data case. The recommendation favors TVmaze because it has the fewest setup dependencies and a clear search-to-save path; it does not claim any free service is outage-proof.

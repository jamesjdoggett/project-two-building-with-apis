# ShowVault

Private TV show tracking website and REST API for discovering shows through TVmaze and managing saved metadata, notes, ratings, and viewing progress.

## Approved references

- Requirements and scope: [PRD](prd/showvault.md).
- Approved work breakdown: [implementation plan](plans/showvault.md).
- Provider findings: [TVmaze research](research/api-provider-comparison.md).
- Selected behavior reference: [watch-progress prototype](prototypes/watch-progress.html); implement the PRD's approved Independent policy in Django.

## Technology and workflow

- Python 3.14, Django, Django REST Framework, and SQLite; manage dependencies and the lockfile with uv.
- Tailwind CSS and DaisyUI through django-tailwind-cli; locally served HTMX with Django-rendered fragments.
- Automated testing: pytest and pytest-django; linting and formatting: Ruff.
- Use `uv sync --locked` for locked dependency installation and `uv run` for project commands.
- Layout: `config/` holds Django configuration; `shows/` owns application code, templates, and pytest tests; the console experiment remains separate.

## Project-wide guidance

- Use one `shows` app and a configuration package, with conventional Django models, forms, views, templates, authentication, and admin.
- Administrators create ordinary accounts; require authentication and owner-scoped access on website, HTMX, and API endpoints, including for staff.
- Use Django sessions and standard CSRF protection; website mutations and logout require POST, and foreign entry lookups return 404.
- Store independent per-user metadata snapshots; share save/refresh operations and personal validation across website and API.
- Keep TVmaze HTTP behavior in a small client; local library operations remain independent of provider availability.
- Deliver usable vertical slices with meaningful automated tests and manual verification following the approved plan.
- Update this file during implementation only for verified project-wide conventions, important commands, or architectural decisions; keep individual additions to 1–6 lines whenever possible.
- Checks: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run python manage.py check`, and `uv run python manage.py makemigrations --check --dry-run`.
- Setup/run: `uv run python manage.py migrate`, `uv run python -X utf8 manage.py tailwind build`, and `uv run python manage.py runserver`; CSS source is `styles/app.css` and output is `static/css/tailwind.css`.
- Provider requests use `shows/tvmaze.py` and its shared `request_gate`: one request/second across users/threads in one local server process; 429 Retry-After guidance extends the cooldown.
- Browser failure fixtures: `uv run python manage.py discovery_demo timeout` starts a DEBUG-only loopback server; other verified scenarios and expected results are documented in README.md.
- Reuse `shows.operations.save_entry(owner, tvmaze_id)`, returning `(entry, created)`; owned duplicates bypass HTTP, database uniqueness recovers collisions, and `SaveBusy` requires explicit retry feedback for SQLite locks. Never hold a write transaction during provider HTTP.
- Personal validation lives in `shows/personal.py`: pass the complete parsed personal state to `validate_personal_fields`; `PERSONAL_FIELDS` defines the editable field allowlist.
- Reuse `shows.library.library_entries(owner, params)` for owner-scoped local lists; it returns the ordered queryset and normalized `q`, `status`, and `sort` controls.

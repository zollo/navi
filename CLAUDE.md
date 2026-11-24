# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Navi gives every user **one simple public page** for their important links, at `/<handle>`: avatar, title, tagline, a row of social icons, and link cards grouped under section headings. Users sign up, claim a handle and edit their page in the web UI.

## Commands

Full stack (Docker; `docker-compose.override.yml` is auto-merged for hot reload):
```bash
make up                      # creates .env from .env.example if missing, then compose up --build
docker compose -f docker-compose.yml up --build   # prod-like, no dev override
```

Backend (`cd backend`):
```bash
pip install ".[dev]"
ruff check .
pytest -q                                        # SQLite; no services needed
NAVI_TEST_DATABASE_URL=postgresql+asyncpg://navi:navi@localhost:5432/navi pytest -q   # same suite on Postgres
pytest tests/test_pages.py::test_avatar
alembic upgrade head && alembic check            # migrations apply and match the models
python -m app.openapi_export ../docs/openapi.json   # or `make openapi`
uvicorn app.main:app --reload
```

Frontend (`cd frontend`):
```bash
npm install
npm run dev          # Vite on :5173; set VITE_API_BASE_URL=http://localhost:8000
npm run build        # tsc (strict, noUnused*) + vite build
npm test             # vitest
```

## Architecture

**Services:** `backend` (FastAPI, REST at `/api`), `frontend` (React/Vite SPA served by nginx), Postgres. No queue/worker.

**Service layer.** `app/services/*` hold all logic and permission checks and raise `core/errors.NaviError` subclasses; routes (`app/api/routes/*`) stay thin and an exception handler in `main.py` maps errors to HTTP. `docs/openapi.json` is the published contract (CI fails if stale; `make openapi`).

**Data model** (`models/page.py`): `users` 1–0..1 `pages` (unique `user_id`, unique lowercase `handle`) → ordered `social_links` (icon + url) and ordered `sections` (optional title) → ordered `links` (title, url, icon). Order is an integer `position`.

**Editing is whole-page.** `PUT /api/pages/me` creates or replaces the caller's page: handle, header, socials and every section with its links, in display order. Children are replaced wholesale (delete-orphan), so there are no reorder/move endpoints. `GET /api/pages/{handle}` is public; `GET /api/pages/handles/{handle}` checks availability.

**Handles** (`services/page_service.py`): `HANDLE_RE` (3–30 chars, `a-z0-9._-`, alphanumeric ends, no `..`) and `RESERVED_HANDLES`. Pages live at the top level of the SPA, so **every top-level SPA route or nginx path must be in `RESERVED_HANDLES`** (and in `frontend/src/lib/page.ts`, which mirrors it for instant feedback). `tests/test_app_smoke.py` checks the main ones.

**URLs** must start with `https://`, `http://` or `mailto:` (`schemas/page.py`), which blocks `javascript:`/`data:` links. Public links render with `rel="noopener noreferrer nofollow"`.

**Icons** (`models/page.Icon`) are stored as VARCHAR (`models/base.str_enum`), so adding one needs no migration: add the enum value, the `IconName` type in `frontend/src/types`, and an entry in `frontend/src/lib/icons.tsx` (react-icons: Font Awesome 6 brands, Lucide for generic). `guessIcon` picks one from a pasted URL's host.

**Avatars:** bytes live in Postgres (`pages.avatar`, deferred column) so the API is stateless. PNG/JPEG/WebP/GIF only (no SVG), `MAX_AVATAR_KB`. `avatar_url` carries `?v=<avatar_version>` so it can be cached. The editor never uploads the picked file directly: `components/AvatarEditor.tsx` (crop/zoom/rotate/flip on a canvas) re-encodes it as a ≤512px square WebP (JPEG where the browser can't encode WebP), stepping quality then size down (`lib/avatar.ts`) until it fits under `max_avatar_kb` from the public `GET /api/config`. So any image the browser can decode works (HEIC on Safari, AVIF), and animated GIFs become stills.

**Auth:** email + password, `Authorization: Bearer <session JWT>` from `/api/auth/login` or `/api/auth/register`, stored in localStorage by the SPA. `ALLOW_REGISTRATION` toggles sign-up.

**Frontend:** `components/PageView.tsx` renders a page and is shared by the public route (`pages/PublicPage.tsx`) and the editor's live preview (`pages/Editor.tsx`). The SPA calls relative `/api`; nginx proxies `/api`, `/docs`, `/redoc`, `/openapi.json` to `backend:8000` via Docker's resolver so nginx boots even when the backend is down. In k8s the ingress routes those paths instead. In Vite dev the API is cross-origin, so image URLs are prefixed with `api.baseUrl`. Mobile-first CSS: bottom tab bar under 760px, 44px touch targets, 16px inputs.

**Build info:** `APP_VERSION`/`GIT_COMMIT`/`BUILD_TIME` build-args are baked into both images (backend `NAVI_*` env, frontend `VITE_*`), surfaced by `GET /api/build-info` and the Account page. Keep these ARGs late in the Dockerfiles.

## Gotchas

- **Tests** run the real app on SQLite with `NullPool` (`DB_NULL_POOL`): async DB connections are bound to the loop that opened them, and `TestClient` runs the app on its own loop. Set `NAVI_TEST_DATABASE_URL` to run the same suite on Postgres (CI does).
- After `commit()`, `await db.refresh(obj)` before returning ORM rows: `updated_at` is server-side and would otherwise lazy-load outside the async greenlet. Changing only child rows doesn't touch the page row, so `save_page` bumps `updated_at` itself.
- Don't annotate 204 routes with `-> None`; return `Response(status_code=204)`.
- bcrypt ≥ 5 raises on passwords > 72 bytes; `core/security.py` truncates explicitly.
- SQLAlchemy relationship forward refs stay quoted; ruff `UP037` is intentionally ignored.
- Starlette's `TestClient` needs `httpx2` (dev dependency).
- **TypeScript:** import `type FormEvent` / `type ReactNode` / `type MouseEvent` from `react`; don't use the `React.*` namespace.
- **Healthchecks:** frontend checks must hit `127.0.0.1`, not `localhost` (busybox wget tries `::1`; nginx listens IPv4-only).

## CI, releases & conventions

`.github/workflows/ci.yml`: backend (ruff, pytest on SQLite, `docs/` drift check), backend-postgres (migrations + `alembic check` + pytest on Postgres), frontend (build + vitest), smoke (base compose boots the whole stack; checks health, the nginx proxy, SPA fallback for `/<handle>`, `/openapi.json`), chart-lint. **Only on push to `main`:** `version` computes the next semver (seeded at `v1.0.0`; `mathieudutour/github-tag-action` thereafter) and creates a GitHub release; `api-spec` attaches the versioned OpenAPI spec; `images` builds both images tagged `latest`/`X.Y.Z`/`X.Y`/`sha-<short>`, signs them with cosign and attests provenance; `chart` publishes the Helm chart.

The repo is **squash-merge only**, with the squash commit title = PR title. The PR title drives the version bump and must be a Conventional Commit (enforced by `.github/workflows/pr-title.yml`): `feat:` → minor, `fix:`/other types → patch, `!` or a `BREAKING CHANGE` footer → major. See `CONTRIBUTING.md`.

## Deployments

- `docker-compose.yml` (+ dev override) — local/dev; builds images from source.
- `deploy/truenas/` — TrueNAS SCALE compose using the published GHCR images; only the frontend port (default 30083, next to Azuregos 30080, Trove 30081 and Tabula 30082) is published.
- `charts/navi/` — Helm chart, published by CI to `oci://ghcr.io/zollo/charts/navi` (version = release). The backend runs `alembic upgrade head` in an init container and can scale horizontally.
- Long-form documentation lives in Notion (linked from the README); keep the README brief and this file current.

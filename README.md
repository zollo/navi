# Navi

One simple page for all of your important links. Sign up, claim a handle, and
share `https://<your-navi>/<handle>`: your photo, a tagline, a row of social
icons, and link cards grouped under headings. Pages can also be served on the
owner's own domain (`www.example.com`), verified through DNS.

**Full documentation lives in [Notion](https://app.notion.com/p/4221d6dd324881f9bc57f5611fb8bfb7)**
(requirements, data model, API, configuration, deployment and roadmap). This
README only covers getting started.

## Quick start

```bash
make up          # copies .env.example to .env if missing, then docker compose up --build
```

Open http://localhost:8080, choose **Create your page**, and claim a handle. The
API is on http://localhost:8000 (interactive docs at `/docs`).

## Development

```bash
cd backend && pip install ".[dev]" && ruff check . && pytest -q
cd frontend && npm install && npm run build && npm test
```

See [CLAUDE.md](CLAUDE.md) for the commands and architecture notes, and
[CONTRIBUTING.md](CONTRIBUTING.md) for branching and PR-title rules (squash
merges, Conventional Commits drive the release version).

## Stack

FastAPI · SQLAlchemy 2 (async) · Alembic · Postgres · React + Vite + TypeScript
served by nginx · Docker Compose, a TrueNAS SCALE compose in `deploy/truenas/`,
and a Helm chart in `charts/navi/` (published to `oci://ghcr.io/zollo/charts/navi`).

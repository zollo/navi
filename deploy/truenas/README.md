# Navi on TrueNAS SCALE

A Docker Compose deployment tuned for **TrueNAS SCALE (Electric Eel 24.10+)**,
which runs Docker natively.

## Why this compose is TrueNAS-friendly

- **Prebuilt images** from GHCR — TrueNAS pulls, it doesn't build.
- **One published port.** The frontend reverse-proxies `/api` to the backend, so
  public pages, the editor and the REST API are all on `http://<truenas>:30083`
  with no CORS and no baked API URL. Postgres and the API stay on the internal
  network. (30083 so it sits next to Azuregos on 30080, Trove on 30081 and Tabula on
  30082.)
- **Data on a dataset.** Postgres (the source of truth, including avatars) is
  bind-mounted to a host dataset you can snapshot and replicate.

## 1. Create the dataset

In the TrueNAS UI: **Datasets → Add Dataset**, e.g. `tank/apps/navi` (swap
`tank` for your pool). The Postgres data lands in a `postgres` subfolder created
automatically on first run.

## 2. Configure

Every setting — **including all secrets** (`SECRET_KEY`, `POSTGRES_PASSWORD`) —
is a plain environment variable: a `.env`
file next to `docker-compose.yml` (Dockge / `docker compose`), the shell, or the
TrueNAS Custom App *Environment Variables* section.

`SECRET_KEY` is required: the stack refuses to start without it.

```bash
cp .env.example .env
openssl rand -hex 32        # SECRET_KEY
openssl rand -hex 16        # POSTGRES_PASSWORD
```

Also set `NAVI_DATA` to your dataset path, `NAVI_PORT` to the host port, and
`NAVI_PUBLIC_URL` to how people (and AI tools) will reach it.

> Changing `POSTGRES_PASSWORD` after the first run won't update an
> already-initialized database. Set it before the first `up`.

## 3. Install

**Option A — Dockge / docker compose (recommended).** Put `docker-compose.yml`
and `.env` in a folder on a dataset and run `docker compose up -d`.

**Option B — TrueNAS "Custom App".** Apps → Discover Apps → **Custom App** →
*Install via YAML*. Paste `docker-compose.yml` and either replace the `${...}`
placeholders with literal values or add the variables in the app's environment
section.

## 4. First use

Open `http://<truenas-ip>:30083`, choose **Create your page**, sign up and claim
a handle. Your page is then public at `NAVI_PUBLIC_URL/<handle>`. To stop new
sign-ups once your own accounts exist, set `ALLOW_REGISTRATION=false`.

## 5. Backups

Snapshot (and optionally replicate) the `NAVI_DATA` dataset — it holds the full
Postgres database: accounts, pages, links and avatars.

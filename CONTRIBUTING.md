# Contributing to Navi

## Branching & merging

- Branch off `main` for every change (`feat/…`, `fix/…`, `ci/…`, `docs/…`).
- Open a PR into `main`. CI (lint, tests, smoke, chart lint) must pass.
- PRs are **squash-merged**; the **PR title becomes the commit subject** on
  `main`, and the merged branch is deleted automatically.

## Conventional Commits

The **PR title must follow [Conventional Commits](https://www.conventionalcommits.org/)**,
because it becomes the squash commit that drives automated semantic versioning
on merge to `main`. A CI check (`PR Title`) enforces this.

```
<type>[optional scope][!]: <description>
```

**Types** and their effect on the next release version:

| Type | Example | Version bump |
|------|---------|--------------|
| `feat` | `feat: let people pin a featured link` | **minor** (x.**Y**.0) |
| `fix` | `fix: keep link order after saving` | **patch** (x.y.**Z**) |
| `feat!` / `fix!` / any `!` | `feat!: require API keys for the REST API` | **major** (**X**.0.0) |
| `docs`, `chore`, `ci`, `build`, `refactor`, `perf`, `test`, `style`, `revert` | `docs: document avatar limits` | patch (default) |

A breaking change can also be signalled with a `BREAKING CHANGE:` footer in the
PR body.

### Guidelines
- Keep the subject imperative and lowercase, no trailing period
  (e.g. `fix: handle empty sections`, not `Fixed the bug.`).
- Use a scope when it helps: `feat(editor): …`, `fix(ui): …`.

## API changes

After changing the REST API, regenerate the published contract and commit it:

```bash
make openapi    # writes docs/openapi.json
```

CI fails if `docs/` is stale. Adding a top-level frontend route? Add it to
`RESERVED_HANDLES` in `backend/app/services/page_service.py` (and the mirror in
`frontend/src/lib/page.ts`) so no page can claim that handle.

## Database changes

Add a migration under `backend/app/migrations/versions/`, chained via
`down_revision`. CI runs `alembic upgrade head && alembic check` against Postgres,
so a model change without a matching migration fails the build.

## Releases

On merge to `main`, CI computes the next `vX.Y.Z` from the PR title, tags it,
creates a GitHub release (with the OpenAPI spec attached), builds/signs/attests the container images (`latest`, `X.Y.Z`, `X.Y`,
`sha-<short>`) and publishes the Helm chart.

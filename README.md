# Job Offer Funnel

A self-hosted tool that treats a job search as a sales funnel: it collects offers from job
boards and company career pages, filters them against explicit rules, and tracks every
application from first contact to signed offer — with conversion metrics per stage and per
channel.

Single-user by design: one person, one token, their own database.

## What it does

- **Inbox** — imports offers every 6 hours from public job-board feeds (Remotive, Himalayas,
  Jobicy, RemoteOK…), RSS, ATS career pages (Greenhouse, Lever, Ashby) and email alerts read
  over IMAP.
- **Rules, not black boxes** — offers are matched against search profiles (titles, location,
  work mode, exclusions). Every filtered offer says which rule filtered it, and nothing is
  lost: filtered offers can be reviewed and rescued.
- **Criteria you can test before applying them** — a change to a rule is previewed against
  the history first: what it would add, what it would remove, with undo.
- **Optional AI assistance** — an LLM can extract facts from an offer's description (work
  mode, location eligibility) with the literal sentence as evidence, and propose rule
  changes. It never decides on its own; the app works without it.
- **Pipeline** — applications move through a stage state machine (evaluated → applied →
  screening → interviewing → offer → accepted) with dated history and explicit outcomes
  (rejected, ghosted, withdrawn, offer declined).
- **Metrics** — conversion by stage and by channel, active pipeline, and offer-quality
  indicators (precision of the inbox, rescued near-misses, noise by cause).

## Architecture

```
frontend/   React + Vite + TypeScript, MUI, TanStack Query
backend/    FastAPI (async), modular monolith
  src/funnel/core/       config, DB session per request, error contract, auth, logging, clock
  src/funnel/modules/    applications · companies · discovery · inbox · metrics
specs/      Gherkin features — the source of truth for behaviour
```

Each backend module is split into `domain` → `service` → `repository` → `router`.
The boundaries are enforced, not just documented: `import-linter` fails the build if `core`
depends on a module, if a layer imports upward, or if a domain imports a framework.

Some decisions worth calling out:

- **Spec-first.** Every feature starts as a Gherkin scenario (32 feature files, 500+
  scenarios), run by `pytest-bdd` on the backend and `playwright-bdd` end-to-end.
- **Typed contract, generated not written.** The frontend's API types are generated from
  `backend/openapi.json`; CI regenerates them and fails if they drift.
- **No CORS.** The frontend calls `/api` on the same origin (Vite proxy in development,
  nginx in Docker).
- **Avoid over-engineering.** A pattern, layer or dependency enters only when a concrete
  problem needs it, and the trigger is written down.

## Stack

| Layer | Tools |
|---|---|
| Backend | Python 3.14, FastAPI, Pydantic v2, SQLAlchemy 2 (async) + asyncpg, Alembic, structlog |
| Database | PostgreSQL |
| Frontend | React, Vite, TypeScript (strict), MUI + MUI X (DataGrid, Charts), TanStack Query, React Router, react-hook-form |
| Quality | ruff, mypy (strict), import-linter, pre-commit, Biome |
| Tests | pytest (unit, integration with Testcontainers, BDD, contract, migrations), Vitest + Testing Library + MSW, Playwright |
| Delivery | Docker Compose, `just`, GitHub Actions, Render |

## Running it

Requirements: Docker, [uv](https://docs.astral.sh/uv/), [just](https://just.systems/) and Node.js.

```bash
cp .env.example .env      # set AUTH_TOKEN and the database credentials
just setup                # install dependencies and git hooks, start the DB, migrate
just up                   # web app, API and database in Docker
```

- App: http://localhost:8081
- API docs (Swagger UI): http://localhost:8080/docs

For development with hot reload, run `just dev` (API on :8000) and `just frontend-dev`
(app on :5173) side by side.

## Tests and CI

```bash
just ci            # backend + frontend: lint, types, architecture, all test suites
just backend-ci
just frontend-ci
just frontend-e2e  # Playwright scenarios from specs/ui/
```

GitHub Actions runs the backend and frontend checks on every push and pull request, checks
migrations on pull requests, and a scheduled workflow triggers the offer import.

## Documentation

Design notes live in `docs/` (in Spanish): the funnel model (`funnel.md`), scope of each
phase (`mvp.md`, `fase0.md`, `fase1.md`), frontend decisions (`frontend.md`) and a
Spanish–English glossary (`glossary.md`). Changes are tracked in `CHANGELOG.md`.

## License

[MIT](LICENSE)

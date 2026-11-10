set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]
set dotenv-load
set working-directory := "backend"

compose := "docker compose -f ../docker-compose.yml"
pytest := "uv run pytest -q --tb=short -rfE"
db_user := env("POSTGRES_USER", "funnel")
db_name := env("POSTGRES_DB", "funnel")

# List recipes
default:
    @just --list

# Install dependencies and git hooks, start the database and migrate
setup:
    uv sync
    just frontend-install
    uv run pre-commit install
    just db-up
    just migrate

# Run the web app, the API and its database in Docker (app at http://localhost:8081, Swagger UI at http://localhost:8080/docs)
up:
    {{compose}} --profile app up -d --build --wait

# Stop the web app, the API and the database (data is kept)
down:
    {{compose}} --profile app down

# Register the job boards of backend/seeds/job_boards.json in the API of `just up` (skips existing ones)
seed-job-boards:
    uv run python scripts/seed_job_boards.py seeds/job_boards.json

# Import the offers of every feed and watched company (API of `just up`, or API_URL)
import-offers:
    uv run python scripts/import_offers.py

# Follow the API logs
logs:
    {{compose}} --profile app logs -f api

# Start local Postgres (waits until healthy)
db-up:
    {{compose}} up -d --wait db

# Stop local Postgres
db-down:
    {{compose}} down

# Back up the database to backups/ (custom pg_dump format, restorable with db-restore)
db-backup:
    {{compose}} exec -T db pg_dump -Fc -U {{db_user}} -d {{db_name}} -f /tmp/backup.dump
    {{compose}} cp db:/tmp/backup.dump ../backups/{{db_name}}-{{datetime("%Y%m%d-%H%M%S")}}.dump
    {{compose}} exec -T db rm /tmp/backup.dump

# Replace the database contents with a backup made by db-backup
[confirm("This replaces all current data with the backup. Continue?")]
db-restore file:
    {{compose}} cp "{{join(invocation_directory(), file)}}" db:/tmp/restore.dump
    {{compose}} exec -T db pg_restore --clean --if-exists --no-owner -U {{db_user}} -d {{db_name}} /tmp/restore.dump
    {{compose}} exec -T db rm /tmp/restore.dump

# Drop the local database volume (ALL DATA), start again and migrate
[confirm("This deletes ALL the data in the local database. Run `just db-backup` first. Continue?")]
db-reset:
    {{compose}} down -v
    just db-up
    just migrate

# Open psql in the local database
db-shell:
    {{compose}} exec db psql -U {{db_user}} -d {{db_name}}

# Apply all migrations
migrate:
    uv run alembic upgrade head

# Create a migration from model changes
migration message:
    uv run alembic revision --autogenerate -m "{{message}}"

# Revert the last migration
downgrade:
    uv run alembic downgrade -1

# Run the API with auto-reload (Swagger UI at http://localhost:8000/docs)
dev:
    uv run uvicorn funnel.main:create_app --factory --reload

# Format and auto-fix
fmt:
    uv run ruff format .
    uv run ruff check --fix .

# Lint without modifying files
lint:
    uv run ruff check .
    uv run ruff format --check .

# Type check
typecheck:
    uv run mypy

# Check architecture contracts
arch:
    uv run lint-imports

# Lint + type check + architecture
check: lint typecheck arch

# Run all tests in parallel (extra args go to pytest)
test *args:
    {{pytest}} -n auto {{args}}

# Unit tests, serial (no Docker needed)
test-unit:
    {{pytest}} -m unit

test-integration:
    {{pytest}} -n auto -m integration

test-bdd:
    {{pytest}} -n auto -m bdd

test-migrations:
    {{pytest}} -n auto -m migrations

test-contract:
    {{pytest}} -m contract

# Run tests matching an expression, serial (works with breakpoint())
test-one expression:
    {{pytest}} -k "{{expression}}"

# Tests with coverage report
cov:
    {{pytest}} -n auto --cov=funnel --cov-report=term-missing

# Export the OpenAPI contract to backend/openapi.json and regenerate the frontend types
openapi:
    uv run python -m funnel.openapi
    just frontend-types

# Install the frontend dependencies
[group("frontend")]
[working-directory("../frontend")]
frontend-install:
    pnpm install --frozen-lockfile

# Run the frontend with hot reload (http://localhost:5173, /api proxied to `just dev`)
[group("frontend")]
[working-directory("../frontend")]
frontend-dev:
    pnpm dev

# Regenerate the frontend API types from backend/openapi.json (`just openapi` runs it)
[group("frontend")]
[working-directory("../frontend")]
frontend-types:
    pnpm run api:types

# Format and auto-fix the frontend
[group("frontend")]
[working-directory("../frontend")]
frontend-fmt:
    pnpm run fmt

# Frontend lint + type check + API types in sync with openapi.json
[group("frontend")]
[working-directory("../frontend")]
frontend-check:
    pnpm run lint
    pnpm run typecheck
    pnpm run api:check

# Frontend component tests (extra args go to vitest)
[group("frontend")]
[working-directory("../frontend")]
frontend-test *args:
    pnpm run test {{args}}

# Frontend E2E: specs/ui scenarios in Chromium against a real API with a throwaway database (needs Docker)
[group("frontend")]
[working-directory("../frontend")]
frontend-e2e *args:
    pnpm run e2e {{args}}

# Backend only: everything its CI job runs (lint, types, architecture, all tests)
backend-ci: check test

# Frontend only: everything its CI job runs (lint, types, API types drift, tests). No Docker
[group("frontend")]
frontend-ci: frontend-check frontend-test

# Backend and frontend: everything CI runs
ci: backend-ci frontend-ci frontend-e2e

# Start Claude Code with Remote Control (controllable from the Claude mobile app)
[no-cd]
claude:
    claude --remote-control "job_offer_funnel"

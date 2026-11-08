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
    uv run pre-commit install
    just db-up
    just migrate

# Start local Postgres (waits until healthy)
db-up:
    {{compose}} up -d --wait

# Stop local Postgres
db-down:
    {{compose}} down

# Drop the local database volume, start again and migrate
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

# Export the OpenAPI contract to backend/openapi.json
openapi:
    uv run python -m funnel.openapi

# Everything CI runs
ci: check test

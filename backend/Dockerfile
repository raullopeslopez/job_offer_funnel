FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first: this layer is reused until uv.lock changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --locked --no-dev

RUN useradd --create-home funnel
USER funnel

EXPOSE 8000

# Migrate on every start: upgrading an up-to-date database does nothing.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn funnel.main:create_app --factory --host 0.0.0.0 --port 8000"]

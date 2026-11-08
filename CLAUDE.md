# Job Offer Funnel

Dashboard para gestionar el proceso de búsqueda de empleo, modelado como un funnel desde el punto de vista del candidato.

## Funnel

Fases: `0 Descubierta → 1 Evaluada → 2 Aplicada → 3 Screening → 4 Entrevistas → 5 Oferta → 6 Aceptada`.

Estados de salida (alcanzables desde cualquier fase, guardando la fase alcanzada): `Rechazado`, `Ghosted`, `Retirado`, `Oferta rechazada`.

Entidades transversales: Empresa, Contacto, Documento (CV/carta versionados), Evento, Tarea, Transición (historial de cambios de fase con fecha), Banco de preguntas.

## Stack (backend)

| Capa | Elección |
|------|----------|
| Lenguaje | Python 3.13 |
| Paquetes / entornos | uv |
| Framework | FastAPI (async) |
| Validación / config | Pydantic v2 + pydantic-settings |
| Base de datos | PostgreSQL |
| Acceso a datos | SQLAlchemy 2 (async) + asyncpg |
| Migraciones | Alembic |
| Jobs en segundo plano | procrastinate (cola sobre Postgres) |
| Auth | Un solo usuario, auth simple; las tablas llevan `user_id` |
| Lint / formato | ruff |
| Tipos | mypy (strict) |
| Tests | pytest + pytest-asyncio + pytest-bdd + pytest-xdist + pytest-cov + testcontainers + httpx + filelock |
| Task runner | just (Justfile en la raíz) |
| Entorno local | Docker Compose (Postgres) |
| Hooks | pre-commit (ruff + mypy) |
| Logging | structlog |
| Repo / CI | GitHub + GitHub Actions (ruff, mypy, pytest) |
| Deploy | Local primero; se decide tras el MVP |
| Integraciones externas | Ninguna en el MVP |

## Metodología: Spec-Driven Development (SDD) con Gherkin

1. **Spec primero.** Cada funcionalidad empieza como un fichero `.feature` en Gherkin (en español, `# language: es`) que describe el comportamiento. No se escribe código de producción sin una spec acordada.
2. **Revisión de la spec** con el usuario antes de implementar.
3. **Los escenarios son tests ejecutables** (pytest-bdd). Primero se ven fallar (rojo).
4. **Implementar** lo mínimo para ponerlos en verde y después refactorizar.
5. Si cambia el comportamiento, se cambia primero la spec.

## Diseño de la API

Flujo: `.feature` → contrato (schemas Pydantic → OpenAPI generado, revisado) → tests BDD en rojo → implementación.

- REST orientado a recursos, prefijo `/api/v1`, recursos en plural y en inglés (`/applications`, `/companies`, `/contacts`).
- **Las transiciones de fase son una acción**: `POST /applications/{id}/transitions {to_stage, date, notes}`. El servicio valida la máquina de estados y guarda el historial. Nunca `PATCH` sobre la fase.
- Sub-recursos solo cuando hay dependencia real: `/applications/{id}/events`, `/applications/{id}/tasks`.
- Métricas como endpoints de solo lectura: `GET /metrics/funnel`, `GET /metrics/stage-durations`.
- Errores en RFC 9457 (`application/problem+json`), con un `type` por cada error de dominio (p. ej. `invalid-transition`).
- IDs UUIDv7. Fechas ISO 8601 en UTC.
- Listados: `limit`/`offset`, filtros por query, `sort`.
- Schemas separados por operación (`XCreate`, `XUpdate`, `XRead`). Nunca exponer modelos ORM.
- Capas: `routers (HTTP) → services (dominio) → repositories (SQLAlchemy)`. El dominio no depende de FastAPI.
- Los tests BDD atacan por HTTP (httpx ASGI) contra Postgres real (testcontainers).

## Arquitectura del repo

Monorepo. Backend organizado por módulos de dominio (verticales), cada uno con sus capas dentro.

```
job_offer_funnel/
├── CLAUDE.md
├── docker-compose.yml           # Postgres local
├── .pre-commit-config.yaml
├── .github/workflows/backend.yml
├── specs/                       # Gherkin: fuente de verdad, agnóstica del front
│   ├── applications/
│   ├── companies/
│   └── metrics/
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── migrations/
│   ├── src/funnel/
│   │   ├── main.py              # app factory, registro de routers
│   │   ├── core/                # config, db, errors, auth, logging
│   │   ├── modules/
│   │   │   ├── <modulo>/
│   │   │   │   ├── domain.py     # reglas y máquina de estados (Python puro)
│   │   │   │   ├── models.py     # ORM
│   │   │   │   ├── schemas.py    # Create/Update/Read
│   │   │   │   ├── repository.py
│   │   │   │   ├── service.py
│   │   │   │   └── router.py
│   │   │   └── metrics/         # solo lectura
│   │   └── jobs/                # tareas procrastinate
│   └── tests/
│       ├── conftest.py          # testcontainers, cliente httpx
│       ├── bdd/                 # step definitions de specs/*.feature
│       ├── unit/                # dominio puro, sin BD
│       └── integration/         # repositories contra Postgres
└── frontend/                    # más adelante
```

Reglas:
- `specs/` vive en la raíz; pytest-bdd la usa vía `bdd_features_base_dir`.
- Un módulo solo usa el `service` de otro módulo, nunca su `repository` ni sus `models`.
- `core` no importa nada de `modules`.
- `domain.py` no importa FastAPI ni SQLAlchemy.
- src layout (`src/funnel/`).

## Tests en paralelo (pytest-xdist)

- `pytest -n auto` por defecto.
- **Un único contenedor Postgres** (testcontainers) compartido entre workers, coordinado con `filelock` (patrón de la doc de xdist).
- Una BD *template* migrada una sola vez; cada worker crea la suya con `CREATE DATABASE test_<worker> TEMPLATE funnel_template` (nombre a partir de `PYTEST_XDIST_WORKER`).
- Aislamiento por test: transacción + rollback; `TRUNCATE` en los tests BDD que hacen commit.
- Para depurar (`breakpoint()`/pdb) se ejecuta sin xdist: `just test-one`.

## Comandos (Justfile)

Todo se ejecuta vía `just` desde la raíz. En Windows: `set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]`.

```
just                    # lista los comandos

# Setup
just setup              # uv sync + pre-commit install + db-up + migrate

# Base de datos
just db-up              # docker compose up -d
just db-down
just db-reset           # tira el volumen, levanta y migra
just db-shell           # psql dentro del contenedor

# Migraciones
just migrate            # alembic upgrade head
just migration "msg"    # alembic revision --autogenerate -m "msg"
just downgrade          # alembic downgrade -1

# Ejecutar
just dev                # uvicorn --reload
just worker             # worker de procrastinate

# Calidad
just fmt                # ruff format + ruff check --fix
just lint               # ruff check + ruff format --check
just typecheck          # mypy
just check              # lint + typecheck

# Tests
just test *args         # pytest -n auto (args extra pasan a pytest)
just test-unit          # solo unit, en serie
just test-integration
just test-bdd
just test-one "expr"    # pytest -k "expr" sin xdist (depuración)
just cov                # pytest -n auto --cov + informe

# SDD
just spec modulo nombre # crea specs/<modulo>/<nombre>.feature desde plantilla
just openapi            # exporta openapi.json para revisar el contrato

# CI
just ci                 # lint + typecheck + test; GitHub Actions llama a esto
```

## Git

- Commits en Conventional Commits.
- **Sin autoría de Claude**: no añadir `Co-Authored-By: Claude`, `Claude-Session` ni ninguna otra línea de atribución en commits ni en PRs.

# Job Offer Funnel

Dashboard para gestionar el proceso de búsqueda de empleo, modelado como un funnel desde el punto de vista del candidato.

## Estilo de respuesta

- Terminar cada respuesta con un resumen de una línea (oneliner), salvo cuando la respuesta ya sea breve, para no ser redundante.

## Estado actual

**Greenfield.** Solo existen `CLAUDE.md` y `docs/`. Todavía **no existen** `backend/`, `specs/`, `Justfile`, `docker-compose.yml` ni CI: los comandos `just` de abajo describen el objetivo y fallarán hasta que se cree el esqueleto. Mantener esta sección actualizada al cerrar cada hito.

Roadmap:
- [x] Concepto del funnel, stack, convenciones
- [ ] Alcance del MVP
- [ ] Esqueleto del backend (pyproject, core, Justfile, docker-compose, conftest con xdist, CI)
- [ ] Primera spec: `specs/applications/stage_transitions.feature`
- [ ] Primer módulo completo (`applications`), que servirá de referencia para el resto

## Funnel

Fases: `0 Descubierta → 1 Evaluada → 2 Aplicada → 3 Screening → 4 Entrevistas → 5 Oferta → 6 Aceptada`.

Estados de salida (alcanzables desde cualquier fase, guardando la fase alcanzada): `Rechazado`, `Ghosted`, `Retirado`, `Oferta rechazada`.

Entidades transversales: Empresa, Contacto, Documento (CV/carta versionados), Evento, Tarea, Transición (historial de cambios de fase con fecha), Banco de preguntas.

Detalle de cada fase (datos, flujo, matices, métricas): `docs/funnel.md`. Leerlo antes de escribir una spec.

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
| Repo / CI | GitHub + GitHub Actions (`just ci`) |
| Deploy | Local primero; se decide tras el MVP |
| Integraciones externas | Ninguna en el MVP |

## Idioma

- **Español**: specs Gherkin (`# language: es`), `docs/`, `CLAUDE.md`.
- **Inglés**: código, nombres de los steps en Python, nombres de tests, commits, rutas y campos de la API, mensajes de error de la API.

## Metodología: Spec-Driven Development (SDD) con Gherkin

Principios:
- No se escribe código de producción sin una spec acordada.
- Los escenarios son tests ejecutables (pytest-bdd).
- Si cambia el comportamiento, se cambia primero la spec.

### Ciclo por feature (checklist)

1. Crear rama `feat/<slug>`.
2. Escribir `specs/<modulo>/<nombre>.feature` (`just spec`). Commit `test(spec): ...`.
3. **⏸ PARAR: pedir revisión de la spec al usuario.** No seguir sin aprobación.
4. Definir el contrato: schemas Pydantic + firmas del router; `just openapi`.
5. **⏸ PARAR: pedir revisión del contrato** (diff de `openapi.json`).
6. Escribir los steps en `backend/tests/bdd/` → ejecutar y verlos **fallar** (rojo). Commit.
7. Implementar: `domain.py` (+ tests unit) → `models.py` + migración (`just migration`) → `repository.py` → `service.py` → `router.py` registrado en `main.py`.
8. Verde → refactor → `just ci` en verde. Commit.
9. Actualizar la sección "Estado actual" si se cierra un hito. Merge a `main`.

### Definition of Done

- Todos los escenarios de la spec pasan.
- `just ci` en verde (ruff, mypy strict, tests con xdist).
- Migración incluida y reversible (`downgrade` funciona).
- `openapi.json` actualizado y coherente con la spec.
- Sin TODOs sin issue asociado.

## Diseño de la API

- REST orientado a recursos, prefijo `/api/v1`, recursos en plural y en inglés (`/applications`, `/companies`, `/contacts`).
- **Las transiciones de fase son una acción**: `POST /applications/{id}/transitions {to_stage, date, notes}`. El servicio valida la máquina de estados y guarda el historial. Nunca `PATCH` sobre la fase.
- Sub-recursos solo cuando hay dependencia real: `/applications/{id}/events`, `/applications/{id}/tasks`.
- Métricas como endpoints de solo lectura: `GET /metrics/funnel`, `GET /metrics/stage-durations`.
- Errores en RFC 9457 (`application/problem+json`), con un `type` por cada error de dominio (p. ej. `invalid-transition`).
- IDs UUIDv7. Fechas ISO 8601 en UTC.
- Listados: `limit`/`offset`, filtros por query, `sort`.
- Schemas separados por operación (`XCreate`, `XUpdate`, `XRead`). Nunca exponer modelos ORM.
- Los tests BDD atacan por HTTP (httpx ASGI) contra Postgres real (testcontainers).

## Arquitectura del repo

Monorepo. Backend organizado por módulos de dominio (verticales), cada uno con sus capas dentro.

```
job_offer_funnel/
├── CLAUDE.md
├── Justfile
├── docker-compose.yml           # Postgres local
├── .env.example
├── .pre-commit-config.yaml
├── .github/workflows/backend.yml
├── docs/                        # documentación de producto (funnel.md)
├── specs/                       # Gherkin: fuente de verdad, agnóstica del front
│   └── <modulo>/*.feature
├── backend/
│   ├── pyproject.toml           # config de ruff, mypy y pytest
│   ├── alembic.ini
│   ├── migrations/
│   ├── src/funnel/
│   │   ├── main.py              # app factory, registro de routers
│   │   ├── core/                # config, db, errors, auth, logging
│   │   ├── modules/<modulo>/
│   │   │   ├── domain.py        # reglas y máquina de estados (Python puro)
│   │   │   ├── models.py        # ORM
│   │   │   ├── schemas.py       # Create/Update/Read
│   │   │   ├── repository.py
│   │   │   ├── service.py
│   │   │   └── router.py
│   │   └── jobs/                # tareas procrastinate
│   └── tests/
│       ├── conftest.py          # testcontainers, BD por worker, cliente httpx
│       ├── bdd/                 # steps; compartidos en bdd/conftest.py
│       ├── unit/                # dominio puro, sin BD
│       └── integration/         # repositories contra Postgres
└── frontend/                    # más adelante
```

Reglas:
- Un módulo solo usa el `service` de otro módulo, nunca su `repository` ni sus `models`.
- `core` no importa nada de `modules`.
- `domain.py` no importa FastAPI ni SQLAlchemy.
- src layout (`src/funnel/`).
- Cuando exista `modules/applications/`, es **el módulo de referencia**: copiar su estructura y patrones para los nuevos módulos.

### Transacciones

- **Una sesión por request**, inyectada como dependency de FastAPI (`get_session` en `core/db.py`).
- La dependency hace `commit` al terminar la request sin errores y `rollback` si hay una excepción.
- **Los services y los repositories nunca hacen `commit`**; como mucho `flush` si necesitan IDs generados.
- Los jobs de procrastinate abren su propia sesión con el mismo patrón.

## Tests

- Markers de pytest (declarados en `pyproject.toml`, con `--strict-markers`): `unit`, `integration`, `bdd`. Todo test lleva su marker; los comandos `just test-*` filtran por él.
- pytest-bdd: `bdd_features_base_dir` apunta a `../specs`. Steps reutilizables en `tests/bdd/conftest.py`; los steps propios de una feature, en `tests/bdd/test_<modulo>_<nombre>.py`.
- Fixtures base (en `tests/conftest.py`): `db_session`, `client` (httpx ASGI), factories de datos.

### En paralelo (pytest-xdist)

- `pytest -n auto` por defecto.
- **Un único contenedor Postgres** (testcontainers) compartido entre workers, coordinado con `filelock` (patrón de la doc de xdist).
- Una BD *template* migrada una sola vez; cada worker crea la suya con `CREATE DATABASE test_<worker> TEMPLATE funnel_template` (nombre a partir de `PYTEST_XDIST_WORKER`).
- Aislamiento por test: transacción + rollback; `TRUNCATE` en los tests BDD que hacen commit.
- Para depurar (`breakpoint()`/pdb) se ejecuta sin xdist: `just test-one`.

## Configuración

- Variables vía pydantic-settings (`core/config.py`), leídas de `.env` (no se versiona). `.env.example` sí se versiona y se mantiene al día.
- Mínimas: `DATABASE_URL` (`postgresql+asyncpg://...`), `LOG_LEVEL`, `AUTH_TOKEN`.

## Windows (entorno de desarrollo)

- **Docker Desktop debe estar arrancado** para `just db-up` y para cualquier test con BD (testcontainers).
- La ruta del home lleva tilde (`C:\Users\Raúl`): puede romper volúmenes de Docker, testcontainers y algunas herramientas. Si algo falla con rutas, sospechar de esto primero (`UV_CACHE_DIR` o `TMP` con rutas ASCII).
- Justfile con `set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]`.

## Comandos (Justfile)

Todo se ejecuta vía `just` desde la raíz.

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
just test-unit          # -m unit, en serie
just test-integration   # -m integration
just test-bdd           # -m bdd
just test-one "expr"    # pytest -k "expr" sin xdist (depuración)
just cov                # pytest -n auto --cov + informe

# SDD
just spec modulo nombre # crea specs/<modulo>/<nombre>.feature desde plantilla
just openapi            # exporta openapi.json para revisar el contrato

# CI
just ci                 # lint + typecheck + test; GitHub Actions llama a esto
```

## Git

- Rama por feature: `feat/<slug>`, `fix/<slug>`. Vida corta.
- Commits por paso del ciclo SDD (spec → steps en rojo → implementación en verde), en Conventional Commits y en inglés.
- Merge a `main` solo con `just ci` en verde. Con remoto en GitHub: PR + CI + squash merge. Sin remoto todavía: merge local.
- **Sin autoría de Claude**: no añadir `Co-Authored-By: Claude`, `Claude-Session` ni ninguna otra línea de atribución en commits ni en PRs.

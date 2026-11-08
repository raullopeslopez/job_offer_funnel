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
| Jobs en segundo plano | procrastinate (cola sobre Postgres); se instala con el primer job real |
| Auth | Un solo usuario, auth simple; las tablas llevan `user_id` |
| Lint / formato | ruff (reglas ampliadas, ver "Clean code") |
| Arquitectura | import-linter (contratos de capas y módulos) |
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
- Migración incluida y reversible (lo verifican los tests `migrations`).
- `openapi.json` actualizado y coherente con la spec (lo verifican los tests `contract`).
- Tests parametrizados donde aplique y siguiendo AAA.
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
- Módulos de referencia: `modules/applications/` para los de modelo de dominio; el primer módulo CRUD que se cree será la referencia de los CRUD. Copiar su estructura y patrones.

### Tipos de módulo: dominio y CRUD (conviven)

Cada módulo declara su tipo en el docstring de su `__init__.py`.

- **Modelo de dominio**: si tiene al menos uno de estos elementos: invariantes entre campos, transiciones de estado, o reglas que dependen del tiempo o de otras entidades. Tiene `domain.py` con entidades propias (dataclasses con comportamiento, sin ORM); el repository mapea ORM ↔ dominio. Hoy: `applications`.
- **CRUD**: sin reglas de negocio. Sin `domain.py`; el service trabaja directamente con los modelos ORM. Hoy: `companies`, `contacts`, `documents`, `events`, `tasks`, `questions`.
- **Las capas externas son idénticas en ambos**: `router → service → repository`, los mismos schemas, los mismos errores, las mismas reglas de import-linter.
- **Regla de promoción**: en cuanto un módulo CRUD necesita su primera regla de negocio, se promueve a modelo de dominio en ese mismo cambio. Nunca se mete la regla en el service ni en el router.

## Patrones

**Regla general: un patrón entra cuando aparece el problema concreto que resuelve, no antes.** Cada patrón aplazado lleva escrito su disparador.

### Adoptados
- Repository, Service Layer, inyección de dependencias (`Depends`), Value Objects, sesión por request como unidad de trabajo.
- **Máquina de estados declarativa**: las transiciones permitidas son datos (`ALLOWED_TRANSITIONS: Mapping[Stage, frozenset[Stage]]` en `applications/domain.py`), no `if` dispersos ni una clase por estado. Los `Outcome` se permiten desde cualquier fase no terminal. La tabla alimenta directamente los tests parametrizados.
- **Métricas con SQL directo**: el módulo `metrics` hace queries dedicadas (CTEs, window functions) sobre `transitions`. No carga entidades de dominio ni usa repositories CRUD.
- `Clock` inyectado.

### Aplazados (con disparador)

| Patrón | Disparador |
|--------|-----------|
| procrastinate (dependencia y worker) | El primer job real (ghosting, follow-up). Hasta entonces no se instala |
| Encolar jobs en la misma transacción | El primer job. **Verificar antes** que procrastinate puede compartir la conexión con SQLAlchemy async/asyncpg; no darlo por hecho |
| Domain events | Cuando una acción de dominio dispare 2 o más efectos secundarios. Hasta entonces, el service encola el job directamente |
| Ports & Adapters / Strategy por portal | Implementar la fase 0 (ingesta de ofertas) |

### Descartados / antipatrones
- `BaseRepository[T]` genérico: repositories explícitos por módulo.
- God services: partir por caso de uso cuando un service crezca demasiado.
- Mediator o bus de comandos.
- DDD completo (aggregates estrictos, bounded contexts formales): se toman las ideas, no el ritual.
- Specification pattern.
- Interfaces (`Protocol`) con una sola implementación.

### Transacciones

- **Una sesión por request**, inyectada como dependency de FastAPI (`get_session` en `core/db.py`).
- La dependency hace `commit` al terminar la request sin errores y `rollback` si hay una excepción.
- **Los services y los repositories nunca hacen `commit`**; como mucho `flush` si necesitan IDs generados.
- Los jobs (cuando existan) abren su propia sesión con el mismo patrón.

## Clean code

### Naming
- Términos de dominio según el glosario `docs/glossary.md` (ES → EN). Un concepto nuevo se añade primero al glosario.
- Nombres que revelan intención, sin abreviaturas (`application`, no `app`).
- Prohibidos los nombres genéricos: `utils`, `helpers`, `manager`, `data`, `info`, `common`.
- Booleanos con `is_`/`has_`/`can_`; funciones con verbo; clases con sustantivo.
- Un concepto, una palabra (si es `create`, nunca mezclar con `add` o `new`).

### Responsabilidades
- **Routers finos**: solo HTTP (parsear → llamar al service → devolver). Cero lógica.
- **Services**: orquestan (cargar → aplicar la regla de dominio → persistir). Sin SQL ni HTTP.
- **Domain**: reglas y decisiones. Sin I/O.
- Dependencias por constructor (los services reciben sus repositories), compuestas con `Depends`. Nada de parchear en los tests.
- Command-query separation: una función o cambia estado o devuelve datos.

### Funciones
- Pequeñas y con un solo nivel de abstracción. Máximo 3 argumentos; si hacen falta más, un objeto.
- Sin flags booleanos como parámetro: dos funciones.
- Sin efectos secundarios ocultos.

### Dominio
- `StrEnum` para fases y estados; nunca strings sueltos.
- Value objects inmutables (`@dataclass(frozen=True)`), p. ej. `Salary(amount, currency)` en lugar de dos campos sueltos.
- **Reloj inyectado** (`Clock`): prohibido `datetime.now()` en el dominio y en los services.
- Sin números mágicos: constantes con nombre o config (p. ej. los días de ghosting).

### Errores
- Jerarquía de excepciones de dominio (`DomainError` → `InvalidTransitionError`, ...).
- El mapeo a problem+json se hace en un único sitio: el exception handler de `core/errors.py`.
- Prohibidos el `except` desnudo, tragarse excepciones y devolver `None` para indicar un error.

### Comentarios
- Explican el porqué, no el qué. Si hace falta explicar el qué, renombra o extrae una función. Sin código comentado. Docstrings solo en la API pública que no sea obvia.

### Principios
- YAGNI: sin abstracciones especulativas (nada de `Protocol` para una sola implementación).
- DRY con regla de tres. Boy scout: deja el código que tocas un poco mejor de lo que estaba.

### Automatización
- **ruff**: `E, F, I, N, B, UP, SIM, RET, ARG, ERA, DTZ, PT, TID, C90 (max-complexity 10), PL`.
- **import-linter** (`just check`): capas `router → service → repository`; `domain` sin FastAPI ni SQLAlchemy; `core` sin `modules`; módulos independientes entre sí (solo vía `service`).
- **mypy strict**: sin `Any` explícito salvo justificado con un comentario.

## Tests

### Tipos

| Tipo | Marker | Qué prueba | BD | xdist | Ubicación |
|------|--------|------------|----|-------|-----------|
| Unit | `unit` | Dominio puro: máquina de estados, reglas, cálculos | No | No | `tests/unit/` |
| Integration | `integration` | Repositories, queries no triviales, jobs (llamando a la función con sesión de test) | Sí | Sí | `tests/integration/` |
| BDD | `bdd` | Escenarios Gherkin end-to-end por HTTP | Sí | Sí | `tests/bdd/` + `specs/` |
| Migraciones | `migrations` | `upgrade head → downgrade base → upgrade head`; modelos ORM == esquema migrado (autogenerate sin diff) | Sí | Sí | `tests/migrations/` |
| Contrato | `contract` | OpenAPI generado == `openapi.json` versionado | No | Sí | `tests/contract/` |

- Pirámide: muchos unit, uno o varios BDD por escenario, pocos integration (solo lo que el SQL hace distinto).
- Markers declarados en `pyproject.toml` con `--strict-markers`. Todo test lleva su marker; `just test-*` filtra por él.
- pytest-bdd: `bdd_features_base_dir` apunta a `../specs`. Steps reutilizables en `tests/bdd/conftest.py`; los propios de una feature, en `tests/bdd/test_<modulo>_<nombre>.py`.
- Fixtures base (en `tests/conftest.py`): `db_session`, `client` (httpx ASGI), `clock` (reloj fijo), factories de datos.
- **Factories, no fixtures gigantes**: los datos se crean con factories (`make_application(stage=...)`) que reciben solo lo que el test necesita y ponen defaults válidos en el resto. Prohibidas las fixtures compartidas que montan un escenario grande que cada test usa a medias.

### Parametrización (obligatoria cuando aplique)

- **Prohibidos los micro-tests que solo se diferencian en los datos de entrada o en el resultado esperado.** Se agrupan con `@pytest.mark.parametrize`.
- Cada caso lleva un `id` legible: `pytest.param(Stage.APPLIED, Stage.OFFER, id="applied-to-offer-skips-stages")`.
- En Gherkin, lo equivalente es `Esquema del escenario` + `Ejemplos`, no escenarios copiados.
- Casos típicos: tablas de transiciones válidas e inválidas, validaciones de schemas, cálculos de métricas.
- **No** se parametriza cuando el Arrange o el Assert cambian de estructura: si hace falta un `if` dentro del test, son tests distintos.

### Arrange-Act-Assert (obligatorio)

- Todo test tiene tres bloques marcados con `# Arrange`, `# Act`, `# Assert` (se omite `# Arrange` si no hay preparación).
- **Un solo Act por test.** Un segundo Act significa un segundo test.
- **Un comportamiento por test**: los asserts comprueban una única consecuencia del Act. Si comprueban cosas independientes (p. ej. el estado devuelto y el email enviado), son dos tests.
- Sin lógica en los tests (`if`, bucles, `try`): la variación va en la parametrización.
- En BDD, Given/When/Then es el AAA: los steps `Dado` preparan, `Cuando` actúa (uno solo) y `Entonces` comprueba.
- Nombres que describen el comportamiento: `test_rejects_transition_when_skipping_stages`.

```python
@pytest.mark.unit
@pytest.mark.parametrize(
    ("current", "target"),
    [
        pytest.param(Stage.APPLIED, Stage.OFFER, id="applied-to-offer"),
        pytest.param(Stage.DISCOVERED, Stage.INTERVIEWING, id="discovered-to-interviewing"),
    ],
)
def test_rejects_transition_when_skipping_stages(current: Stage, target: Stage) -> None:
    # Arrange
    application = make_application(stage=current)

    # Act
    with pytest.raises(InvalidTransitionError) as exc_info:
        application.transition_to(target)

    # Assert
    assert exc_info.value.target == target
```

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
just worker             # worker de procrastinate (cuando exista el primer job)

# Calidad
just fmt                # ruff format + ruff check --fix
just lint               # ruff check + ruff format --check
just typecheck          # mypy
just check              # lint + typecheck + import-linter

# Tests
just test *args         # pytest -n auto (args extra pasan a pytest)
just test-unit          # -m unit, en serie
just test-integration   # -m integration
just test-bdd           # -m bdd
just test-migrations    # -m migrations
just test-contract      # -m contract
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

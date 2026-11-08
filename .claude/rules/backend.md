---
paths:
  - "backend/src/**"
  - "backend/migrations/**"
---

# Backend: arquitectura y convenciones

## Estructura

```
backend/src/funnel/
├── main.py              # app factory, registro de routers
├── core/                # config, db, errors, auth, logging, clock
├── modules/<modulo>/
│   ├── __init__.py      # docstring con el tipo de módulo (dominio | CRUD)
│   ├── domain.py        # solo en módulos de dominio
│   ├── models.py        # ORM
│   ├── schemas.py       # Create/Update/Read
│   ├── repository.py
│   ├── service.py
│   └── router.py
└── jobs/                # cuando exista el primer job
```

## Dependencias (las verifica import-linter)

- Capas `router → service → repository`. Nunca al revés ni saltándose una capa.
- Un módulo solo usa el `service` de otro módulo, nunca su `repository` ni sus `models`. El módulo que se deja usar expone `build_<x>_service(session, ...)` en su `service.py`; el que lo usa lo compone en su router con la misma sesión (todo o nada) y declara la excepción en `ignore_imports` del contrato de independencia (hoy: `inbox` → services de `companies` y `applications`).
- Para referenciar a otro módulo basta una FK por nombre de tabla (`ForeignKey("companies.id")`): la existencia la garantiza la BD y el repository traduce la violación a un error 422 (p. ej. `unknown-company`). Sin imports entre módulos.
- `core` no importa nada de `modules`. `domain.py` no importa FastAPI ni SQLAlchemy.

## Tipos de módulo (conviven)

- **Dominio**: tiene al menos uno de estos elementos: invariantes entre campos, transiciones de estado, o reglas que dependen del tiempo o de otras entidades. `domain.py` con dataclasses con comportamiento; el repository mapea ORM ↔ dominio. Hoy: `applications`.
- **CRUD**: sin reglas. Sin `domain.py`; el service usa los modelos ORM. Hoy: `companies`, `contacts`, `documents`, `events`, `tasks`, `questions`.
- **Métricas** (`metrics`): solo lectura, capas `router → queries`. SQL directo sobre las tablas por nombre, sin entidades, service ni repository. Única excepción a la independencia entre módulos: importa los enums de `applications.domain` (declarada en `ignore_imports`).
- Las capas externas son idénticas en dominio y CRUD.
- **Promoción**: la primera regla de negocio de un CRUD lo convierte en dominio en ese mismo cambio. La regla nunca va al service ni al router.
- Referencia: copiar la estructura de `applications` (dominio) o de `companies` (CRUD).

## Transacciones

- Sesión por request vía dependency (`get_session` en `core/db.py`): `commit` al terminar sin errores, `rollback` si hay excepción.
- Services y repositories nunca hacen `commit`; como mucho `flush` para obtener IDs.

## Base de datos

- Enums como `VARCHAR` + `CHECK` (no enums nativos de PG): añadir un valor no exige migrar un tipo. Un `Enum` de SQLAlchemy por columna, para que cada CHECK tenga su propio nombre.
- IDs `uuid.uuid7()` de la stdlib: ordenables por tiempo, desempatan filas creadas el mismo día.
- **Índices**: siempre uno en **cada clave foránea** (Postgres no los crea solo, y sin ellos cada lookup por padre y cada borrado en cascada recorre la tabla entera). Las PK y los `UNIQUE` ya traen el suyo. Cualquier otro índice está aplazado: disparador = una consulta lenta medida con `EXPLAIN ANALYZE`, o una tabla de más de ~10.000 filas.
- Las migraciones autogeneradas se revisan siempre a mano antes del commit.

## Patrones

Un patrón entra cuando aparece el problema concreto que resuelve.

- **Adoptados**: Repository, Service Layer, `Depends`, Value Objects, máquina de estados declarativa (las reglas de avance y de salida por fase son datos en `applications/domain.py`, no `if` dispersos; la fuente de verdad es `specs/applications/stage_transitions.feature`), métricas con SQL directo (CTEs y window functions en `metrics`, sin entidades ni repositories), `Clock` inyectado.
- **Aplazados**:
  - procrastinate: con el primer job real.
  - Encolar jobs en la misma transacción: con el primer job, verificando antes que procrastinate comparte conexión con SQLAlchemy async/asyncpg.
  - Domain events: cuando una acción dispare 2 o más efectos.
  - Adapters por portal: con la fase 0.
  - `user_id` en las tablas: solo si el producto pasa a ser multiusuario. Hoy hay un único usuario y la columna no aportaría nada.
- **Descartados**: `BaseRepository[T]` genérico, god services, Mediator o bus de comandos, DDD completo, Specification, `Protocol` con una sola implementación.

## API

- **Recursos**: REST, `/api/v1`, sustantivos en plural y en inglés. Sub-recursos solo con dependencia real. Una acción que no encaja se modela como un recurso que se crea (p. ej. `POST /applications/{id}/transitions {to_stage | outcome, occurred_on, note}`). Nunca `PATCH` sobre la fase.
- **Métodos**: `GET` lee · `POST` crea (201) · `PATCH` modifica parcialmente (nunca `PUT`) · `DELETE` borra (204).
- **Datos**: JSON en `snake_case`; enums en minúscula; IDs UUIDv7; fechas ISO 8601 (`occurred_on` para días, `*_at` para instantes UTC).
- **Colecciones**: paginación offset con `Depends(get_page_params)` (`limit` 1-100, por defecto 20; `offset` ≥ 0) y respuesta `Page[XRead]` = `{items, total, limit, offset}` (`core/pagination.py`). Filtros por query y `sort` (`-campo` = descendente). Orden siempre determinista (desempate por `id`).
- **Versionado**: cambio compatible (añadir) → sin más; cambio que rompe (quitar o renombrar un campo o un slug de error, cambiar un tipo) → `/v2`. El test de contrato detecta cualquier cambio.
- Schemas `XCreate`/`XUpdate`/`XRead`; nunca exponer modelos ORM.

### Contrato de errores (`core/errors.py`)

- **Toda** respuesta de error es problem+json (RFC 9457): `type`, `title`, `status`, `detail` opcional.
- **Controlados**: cada subclase de `AppError` es un `type` estable (`/problems/<slug>`); renombrar un slug rompe el contrato. Las reglas de dominio lanzan subclases de `DomainError` con un slug específico (p. ej. `invalid-transition`). Nunca se lanza `HTTPException` desde un módulo.
- **Inesperados**: cualquier otra excepción → `500 /problems/internal-error` con `detail` genérico; el traceback va al log. Nunca se expone el mensaje real.
- **Códigos**: 401 token (con `WWW-Authenticate: Bearer`) · 404 no existe · 409 conflicto con el estado actual · 422 datos inválidos (`validation-error` con `errors: [{field, message}]`, o un slug de regla de valor) · 500 inesperado.
- Los errores de BD suben como 500, salvo los que tienen significado de negocio: la unicidad la garantiza un índice `UNIQUE` en la BD (nunca un "¿existe ya?" en Python) y el repository traduce su `IntegrityError` a `AlreadyExistsError` (409 `already-exists`) con `flush_checking_unique` (`core/db.py`). Igual con las FK: borrar algo aún referenciado → `InUseError` (409 `in-use`, por SQLSTATE `23503`). El mensaje del error se construye **antes** del `flush`: tras un flush fallido no se pueden leer los atributos de la fila.
- `title`/`detail` en inglés, para humanos; el cliente decide por `type` (también para la futura i18n).
- Cada endpoint declara en `responses=` los errores que puede devolver (401 y 422 vienen del router `/api/v1`).
- Aplazados: request/correlation id (disparador: deploy con logs concurrentes), URIs absolutas en `type`, campo `instance`.

## Clean code

- **Naming**: términos de `docs/glossary.md`; sin abreviaturas; prohibidos `utils`, `helpers`, `manager`, `data`, `info`, `common`; booleanos `is_`/`has_`/`can_`; funciones con verbo, clases con sustantivo; un concepto, una palabra.
- **Responsabilidades**: routers solo HTTP; services orquestan (sin SQL ni HTTP); domain decide (sin I/O); dependencias por constructor; command-query separation.
- **Funciones**: pequeñas, un nivel de abstracción, máximo 3 argumentos, sin flags booleanos, sin efectos ocultos.
- **Dominio**: `StrEnum` para fases y estados; value objects `frozen` (p. ej. `Salary(amount, currency)`); prohibido `datetime.now()`, se usa `Clock`; sin números mágicos.
- **Errores**: jerarquía `DomainError`; el mapeo a problem+json solo en `core/errors.py`; prohibidos el `except` desnudo, tragarse excepciones y devolver `None` como error.
- **Comentarios**: el porqué, no el qué (si hace falta explicar el qué, renombra o extrae); sin código comentado.
- **Principios**: YAGNI, DRY con regla de tres, boy scout.
- **Herramientas** (`backend/pyproject.toml`): ruff `E, F, I, N, B, UP, SIM, RET, ARG, ERA, DTZ, PT, TID, C90 (max 10), PL`; mypy strict sin `Any` injustificado; import-linter.

## Config

pydantic-settings en `core/config.py` desde `.env` (no versionado); `.env.example` versionado y al día. Variables: `DATABASE_URL` (`postgresql+asyncpg://...`), `LOG_LEVEL`, `AUTH_TOKEN`.

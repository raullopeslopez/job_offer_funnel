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
- Un módulo solo usa el `service` de otro módulo, nunca su `repository` ni sus `models`.
- `core` no importa nada de `modules`. `domain.py` no importa FastAPI ni SQLAlchemy.

## Tipos de módulo (conviven)

- **Dominio**: tiene al menos uno de estos elementos: invariantes entre campos, transiciones de estado, o reglas que dependen del tiempo o de otras entidades. `domain.py` con dataclasses con comportamiento; el repository mapea ORM ↔ dominio. Hoy: `applications`.
- **CRUD**: sin reglas. Sin `domain.py`; el service usa los modelos ORM. Hoy: `companies`, `contacts`, `documents`, `events`, `tasks`, `questions`.
- Las capas externas son idénticas en ambos.
- **Promoción**: la primera regla de negocio de un CRUD lo convierte en dominio en ese mismo cambio. La regla nunca va al service ni al router.
- Referencia: copiar la estructura de `applications` (dominio) o del primer CRUD.

## Transacciones

- Sesión por request vía dependency (`get_session` en `core/db.py`): `commit` al terminar sin errores, `rollback` si hay excepción.
- Services y repositories nunca hacen `commit`; como mucho `flush` para obtener IDs.

## Patrones

Un patrón entra cuando aparece el problema concreto que resuelve.

- **Adoptados**: Repository, Service Layer, `Depends`, Value Objects, máquina de estados declarativa (`ALLOWED_TRANSITIONS: Mapping[Stage, frozenset[Stage]]`; los `Outcome` se permiten desde cualquier fase no terminal), métricas con SQL directo (CTEs y window functions en `metrics`, sin entidades ni repositories), `Clock` inyectado.
- **Aplazados**:
  - procrastinate: con el primer job real.
  - Encolar jobs en la misma transacción: con el primer job, verificando antes que procrastinate comparte conexión con SQLAlchemy async/asyncpg.
  - Domain events: cuando una acción dispare 2 o más efectos.
  - Adapters por portal: con la fase 0.
- **Descartados**: `BaseRepository[T]` genérico, god services, Mediator o bus de comandos, DDD completo, Specification, `Protocol` con una sola implementación.

## API

- REST, `/api/v1`, recursos en plural y en inglés. Sub-recursos solo con dependencia real.
- Transición de fase: `POST /applications/{id}/transitions {to_stage, date, notes}`. Nunca `PATCH` sobre la fase.
- Métricas de solo lectura: `GET /metrics/...`.
- Errores RFC 9457 (problem+json), con un `type` por cada error de dominio.
- IDs UUIDv7; fechas ISO 8601 UTC; listados con `limit`/`offset`, filtros y `sort`.
- Schemas `XCreate`/`XUpdate`/`XRead`; nunca exponer modelos ORM.

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

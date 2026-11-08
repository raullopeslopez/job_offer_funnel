# Job Offer Funnel

Dashboard para gestionar la búsqueda de empleo como un funnel, desde el punto de vista del candidato. Dominio: `docs/funnel.md`. Términos ES → EN: `docs/glossary.md`.

## Estilo de respuesta

Las respuestas que no sean breves terminan con una última línea `**Resumen:** <una frase>`, después de cualquier pregunta o siguiente paso.

## Estado actual

Greenfield: existen `CLAUDE.md`, `docs/` y `.claude/` (rules y skill). Todavía no existen `backend/`, `specs/`, `Justfile` ni CI, así que los comandos `just` fallarán hasta crear el esqueleto. Actualizar esta sección al cerrar cada hito.

- [x] Concepto, stack, convenciones, harness
- [ ] Alcance del MVP
- [ ] Esqueleto del backend (pyproject, core, Justfile, docker-compose, conftest con xdist, CI) + hooks de Claude Code (ruff tras editar, `just check` al terminar)
- [ ] Primera spec: `specs/applications/stage_transitions.feature`
- [ ] Primer módulo completo (`applications`)

## Criterio: evitar la sobreingeniería

- La solución más simple que cumpla la spec. Nada de código, configuración ni abstracciones para requisitos hipotéticos.
- Un patrón, una dependencia o una capa nueva entra solo cuando aparece el problema concreto que resuelve, y se anota su disparador (ver los aplazados en `.claude/rules/backend.md`).
- Generalizar a partir del tercer caso, no del primero.
- Ante la duda entre dos diseños, el que tenga menos piezas. Si una propuesta añade complejidad, justificar qué problema actual resuelve.

## Stack

Python 3.13 · uv · FastAPI (async) · Pydantic v2 · PostgreSQL · SQLAlchemy 2 async + asyncpg · Alembic · ruff · mypy strict · import-linter · pytest (asyncio, bdd, xdist, cov) + testcontainers + httpx · just · Docker Compose · pre-commit · structlog · GitHub Actions. Un solo usuario con auth simple; sin integraciones externas en el MVP; deploy local primero.

## Idioma

Español: specs (`# language: es`), `docs/`, `CLAUDE.md`. Inglés: código, tests, commits y API.

## Desarrollo

- Toda feature sigue el ciclo SDD de la skill `sdd-feature`: spec aprobada → contrato aprobado → rojo → verde → `just ci`.
- Las reglas de cada zona se cargan solas desde `.claude/rules/` (backend, tests, specs, entorno).
- **Definition of Done**: escenarios en verde · `just ci` en verde · migración reversible · `openapi.json` coherente · tests parametrizados y en AAA · sin TODOs sin issue.
- Comandos clave: `just setup` · `just dev` · `just check` · `just test` · `just test-one "expr"` (sin xdist) · `just ci`. Requieren Docker Desktop arrancado.

## Git

- Ramas `feat/<slug>` y `fix/<slug>`, de vida corta. Commits por paso del ciclo, en Conventional Commits y en inglés. Merge a `main` con `just ci` en verde.
- Sin líneas de autoría de Claude en commits ni PRs (`Co-Authored-By`, `Claude-Session`, "Generated with"). Lo garantiza `attribution` en `.claude/settings.json`.

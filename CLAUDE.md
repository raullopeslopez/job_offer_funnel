# Job Offer Funnel

Dashboard para gestionar la búsqueda de empleo como un funnel, desde el punto de vista del candidato. Dominio: `docs/funnel.md`. Términos ES → EN: `docs/glossary.md`. Alcance actual: `docs/mvp.md`.

## Estilo de respuesta

Responder siempre en español, aunque el código, las specs y la salida de las herramientas estén en inglés. Las respuestas que no sean breves terminan con una última línea `**Resumen:** <una frase>`, después de cualquier pregunta o siguiente paso.

## Estado actual

Backend con `core` completo (config, sesión por request, contrato de errores, auth por token, logging, `Clock`) y tres módulos de **referencia**: `applications` (dominio: transiciones de fase, más alta, edición, detalle con historial y listado filtrado), `companies` (CRUD: alta, detalle, listado paginado) y `metrics` (solo lectura, SQL directo: conversión por fase y por canal, pipeline activo). Actualizar esta sección al cerrar cada hito.

- [x] Concepto, stack, convenciones, harness
- [x] Alcance del MVP: `docs/mvp.md` (solo API; las features fuera del MVP no se implementan)
- [x] Esqueleto del backend + hooks de Claude Code. Descartado un subagent test-runner (pytest ya da salida escueta; solo se reconsidera si `/usage` lo justifica)
- [x] Spec + implementación: `applications/stage_transitions`
- [x] Spec + implementación: `companies/manage_companies` (primer módulo CRUD: referencia para los demás)
- [x] Spec + implementación: `applications/manage_applications`
- [x] Spec + implementación: `metrics/funnel_metrics` (MVP completo)
- [x] Alcance de la fase 0: `docs/fase0.md` (búsqueda asistida, portales como datos)
- [x] Spec + implementación: `discovery/search_profiles`
- [x] Spec + implementación: `discovery/job_boards`
- [x] Spec + implementación: `discovery/generated_searches`
- [ ] Specs 4-6 de la fase 0: `inbox`, `ats_companies`, `public_feeds`

## Criterio: evitar la sobreingeniería

- La solución más simple que cumpla la spec. Nada de código, configuración ni abstracciones para requisitos hipotéticos.
- Un patrón, una dependencia o una capa nueva entra solo cuando aparece el problema concreto que resuelve, y se anota su disparador (ver los aplazados en `.claude/rules/backend.md`).
- Generalizar a partir del tercer caso, no del primero.
- Ante la duda entre dos diseños, el que tenga menos piezas. Si una propuesta añade complejidad, justificar qué problema actual resuelve.

## Stack

Python 3.14 (fijado en `backend/.python-version`) · uv · FastAPI (async) · Pydantic v2 · PostgreSQL · SQLAlchemy 2 async + asyncpg · Alembic · ruff · mypy strict · import-linter · pytest (asyncio, bdd, xdist, cov) + testcontainers + httpx2 · just · Docker Compose · pre-commit · structlog · GitHub Actions. Un solo usuario con auth simple; sin integraciones externas en el MVP; deploy local primero.

## Idioma

**Inglés**: todo lo que forma parte del producto: código, tests, specs Gherkin, commits, API y textos de la app. El soporte de otros idiomas (i18n) será una feature futura. **Español**: solo la documentación interna (`docs/`, `CLAUDE.md`, `.claude/`).

## Desarrollo

- Toda feature sigue el ciclo SDD de la skill `sdd-feature`: spec aprobada → contrato aprobado → rojo → verde → `just ci`.
- Las reglas de cada zona se cargan solas desde `.claude/rules/` (backend, tests, specs, entorno).
- **Definition of Done**: escenarios en verde · `just ci` en verde · migración reversible · `openapi.json` coherente · tests parametrizados y en AAA · `CHANGELOG.md` actualizado · sin TODOs sin issue.
- Primera vez: copiar `.env.example` a `.env` y ejecutar `just setup`. Comandos clave: `just up` (API + BD en Docker, para el uso diario; Swagger en `localhost:8080/docs`) · `just dev` (desarrollo con recarga, `localhost:8000/docs`) · `just db-backup` / `just db-restore <fichero>` · `just check` · `just test` · `just test-one "expr"` (sin xdist) · `just ci`. Requieren Docker Desktop arrancado.
- Sesiones con Remote Control (para controlarlas desde Claude mobile): arrancar con `just claude`.

## Git y PRs

- Remoto: `github.com/raullopeslopez/job_offer_funnel` (privado). Nunca se hace commit directo en `main`.
- Ramas `feat/`, `fix/` y `chore/<slug>`, de vida corta. Commits por paso del ciclo, en Conventional Commits y en inglés.
- Al terminar: `just ci` en verde → push de la rama → `gh pr create` hacia `main`, con un resumen y la evidencia de los tests → comprobar el CI con `gh pr checks`.
- **El merge lo hace el usuario.** Claude nunca mergea PRs ni hace push a `main`.
- **Changelog** (`CHANGELOG.md`, formato Keep a Changelog, en inglés): cada PR añade sus cambios en `[Unreleased]` (`Added`, `Changed`, `Fixed`, `Removed`), escritos para quien usa la API: qué puede hacer ahora, no cómo está hecho. Los refactors internos sin efecto visible no entran.
- **Releases**, solo cuando el usuario lo pida: `[Unreleased]` pasa a `[X.Y.Z] - YYYY-MM-DD`, se sube la versión en `backend/pyproject.toml` (única fuente de la versión) y se crea el tag `vX.Y.Z`. SemVer; en `0.x` la API puede cambiar sin subir la versión mayor.
- Sin líneas de autoría de Claude en commits ni PRs (`Co-Authored-By`, `Claude-Session`, "Generated with"). Lo garantiza `attribution` en `.claude/settings.json`.

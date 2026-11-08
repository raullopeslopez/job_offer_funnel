# Alcance del frontend

**Pregunta que responde**: ¿puedo usar todo el flujo, desde descubrir una oferta hasta ver las métricas, sin abrir Swagger?

**Interfaz**: una SPA en `frontend/` que consume la API v1 tal cual. El frontend no añade reglas de negocio: si una pantalla necesita algo que la API no da, se cambia antes la API, con su propio ciclo SDD.

## Stack y tooling

| Necesidad | Herramienta | Equivale en el backend a |
|-----------|-------------|--------------------------|
| Base | React + Vite + TypeScript (strict) | FastAPI |
| Gestor de paquetes | pnpm | uv |
| Sistema de diseño | Material UI, con un único `theme.ts` (color, tipografía, espaciado, forma) | — |
| Listados y gráficas | MUI X DataGrid (community) y MUI X Charts | — |
| Contrato con la API | openapi-typescript (tipos desde `backend/openapi.json`) + openapi-fetch | Pydantic |
| Estado del servidor | TanStack Query (caché e invalidación tras cada cambio) | sesión por request |
| Rutas | React Router (modo librería) | routers |
| Formularios | react-hook-form; los 422 de la API se muestran en su campo | — |
| Lint y formato | Biome | ruff |
| Tipos | `tsc --noEmit` | mypy strict |
| Tests de componente | Vitest + Testing Library + MSW (API simulada con los tipos generados) | pytest |
| E2E | Playwright + playwright-bdd (ejecuta los `.feature`) | pytest-bdd |

## Decisiones

- **Sin CORS**: el frontend llama a `/api` en el mismo origen. En desarrollo, a través del proxy de Vite; en el uso diario, con un servicio `web` en Docker Compose (nginx: sirve el build y reenvía `/api` a la API). `just up` levanta los tres servicios.
- **Auth**: la primera vez, la app pide el `AUTH_TOKEN` y lo guarda en `localStorage`. Si la API devuelve un 401, vuelve a pedirlo. No hay pantalla de login ni usuarios.
- **Tipos generados, nunca escritos a mano**: `just ci` regenera los tipos desde `openapi.json` y falla si cambian. Un cambio en la API no puede romper el frontend en silencio.
- **Specs Gherkin por pantalla** en `specs/ui/<pantalla>.feature`, con las mismas reglas que las del backend (`.claude/rules/specs.md`): comportamiento visible para el usuario, nunca componentes ni endpoints.
- **E2E contra la API real** con su base de datos de test; los `Given` preparan los datos llamando a la API. Los tests de componente usan MSW para los casos difíciles de reproducir (errores, estados vacíos).
- **Solo escritorio, en inglés y con tema claro**, como el resto del producto.

## Ciclo SDD en el frontend

1. **Spec**: `specs/ui/<pantalla>.feature`, aprobada por el usuario.
2. **Contrato**: ruta, componentes principales y endpoints que usa la pantalla. Aquí se detecta si falta algo en la API.
3. **Rojo**: los escenarios de playwright-bdd fallan.
4. **Verde**: implementación y tests de componente.
5. **`just frontend-ci` + `just frontend-e2e`** (o `just ci` si también cambia el backend): Biome, tsc, Vitest, check de deriva de tipos y Playwright.

## PRs, en orden

0. `chore/frontend-setup`: `frontend/` con el stack, el tema, el layout (navegación lateral), la pantalla de token, los tipos generados, el proxy, el servicio `web`, las recetas de `just`, el job de CI y `.claude/rules/frontend.md`. Sin pantallas de dominio. Las dependencias entran con la primera pantalla que las usa: MUI X DataGrid y Playwright + playwright-bdd con la bandeja (1), MUI X Charts con las métricas (5).

Una pantalla por PR, en orden de uso:

| # | Spec | Pantalla | Endpoints |
|---|------|----------|-----------|
| 1 | `specs/ui/inbox.feature` | **Bandeja**: listado de ofertas, alta manual, importar feeds, descartar y deshacer, pasar a candidatura | `offers`, `feeds` |
| 2 | `specs/ui/searches.feature` | **Búsquedas**: perfiles (CRUD) y, por perfil, las búsquedas generadas con su enlace al portal | `search-profiles`, `searches` |
| 3 | `specs/ui/applications.feature` | **Candidaturas**: listado con filtros, alta, edición y detalle con historial | `applications` |
| 4 | `specs/ui/stage_transitions.feature` | **Transiciones** en el detalle: avanzar de fase, salidas y deshacer la última | `transitions` |
| 5 | `specs/ui/metrics.feature` | **Métricas**: conversión por fase y por canal, pipeline activo | `metrics` |
| 6 | `specs/ui/settings.feature` | **Ajustes**: empresas y portales (CRUD) | `companies`, `job-boards` |

## Fuera (con disparador)

| Fuera | Entra cuando... |
|-------|-----------------|
| E2E en paralelo (una BD y una API por worker) | La suite E2E pase de ~3 minutos |
| Storybook | Haya 3 o más componentes propios reutilizados entre pantallas |
| zod (validación en el cliente) | Aparezca una validación que el backend no cubre |
| dependency-cruiser (el import-linter del frontend) | `frontend/src` tenga varias features con fronteras que proteger |
| Tests visuales de regresión | Los cambios de tema empiecen a romper pantallas |
| Tema oscuro | Se pida; el tema único lo deja a un cambio de paleta |
| Móvil / responsive | Se quiera usar la app desde el móvil |
| i18n | Se quiera la app en otro idioma (ver `docs/mvp.md`) |
| Spec 5 de la fase 0 (`ats_companies`) en la UI | Exista en la API |

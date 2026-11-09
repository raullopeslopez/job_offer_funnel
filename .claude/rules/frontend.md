---
paths:
  - "frontend/**"
  - "specs/ui/**"
---

# Frontend: arquitectura y convenciones

Alcance, stack y orden de pantallas: `docs/frontend.md`. Aquí, cómo se trabaja en `frontend/`.

## Estructura

```
frontend/src/
├── main.tsx         # providers: tema, TanStack Query, TokenGate, router
├── router.tsx       # rutas (React Router, modo librería)
├── theme.ts         # único sitio de color, tipografía, espaciado y forma
├── api/
│   ├── schema.d.ts  # GENERADO desde backend/openapi.json: nunca se edita a mano
│   └── client.ts    # cliente openapi-fetch: token en cada petición, 401 → pedir token
├── auth/            # token en localStorage (token.ts) y pantalla del token
├── components/      # componentes visuales compartidos entre pantallas
├── layout/          # navegación lateral; navItems.ts lleva una entrada por pantalla
├── pages/           # una carpeta o fichero por pantalla
└── test/            # setup de Vitest y servidor MSW
```

## Reglas

- **La API, solo a través de `api` (`src/api/client.ts`)**, con las rutas y tipos de `schema.d.ts`. Nada de `fetch` directo ni tipos de la API escritos a mano.
- Si cambia la API: `just openapi` regenera `openapi.json` y los tipos. `just frontend-check` falla si `schema.d.ts` no está al día.
- **Sin reglas de negocio en el cliente**: validan la API y sus 422; el formulario los muestra en su campo (`setError`).
- Estilos con el tema y `sx`; ningún color ni tamaño suelto fuera de `theme.ts`.
- Textos de la app en inglés, como el resto del producto.
- Cada pantalla añade su ruta en `router.tsx` y su entrada en `layout/navItems.ts`.

## Tests

- Vitest + Testing Library + MSW, en `*.test.tsx` junto al componente. AAA con comentarios `// Arrange`, `// Act`, `// Assert`; casos que solo cambian en datos, con `it.each`.
- Buscar por rol, etiqueta o texto visible, nunca por clases ni `data-testid` salvo que no haya otra forma.
- MSW con `onUnhandledFrame: "error"`: cada test declara con `server.use` las peticiones que espera. `localStorage` se limpia tras cada test.
- **E2E** (Playwright + playwright-bdd): ejecuta `specs/ui/*.feature` en Chromium. Steps en `frontend/e2e/*.steps.ts`; `Given`/`When`/`Then` y el fixture `api` salen de `e2e/support/fixtures.ts`.
  - Contra la API real de `backend/tests/support/e2e_server.py` (Postgres de testcontainers, token `e2e-token`, puerto 8001) y un Vite en el 5174 con el proxy hacia ella. Playwright arranca los dos.
  - Cada escenario empieza con la BD vacía (el fixture `api` llama a `POST /e2e/reset`, que solo existe en ese servidor de test). Los `Given` preparan los datos por la API (`e2e/support/api.ts`), nunca por la UI salvo que el paso sea de la UI.
  - Un solo worker: comparten BD. Paralelizar (una BD y una API por worker) entra cuando la suite pase de ~3 minutos.
  - Escenarios con `@component`: los que el E2E no puede reproducir (los feeds públicos). Playwright los excluye y los cubre un test de componente con MSW que cita la spec.
- El listado (DataGrid) lo cubre el E2E; los tests de componente, los diálogos y los casos de MSW.

## Herramientas

- `just frontend-dev` (con `just dev` para la API) · `just frontend-fmt` · `just frontend-check` (Biome, `tsc`, deriva de tipos) · `just frontend-test` · `just frontend-e2e` (necesita Docker; primera vez: `pnpm exec playwright install chromium` en `frontend/`).
- **Cambios solo de frontend: `just frontend-ci` + `just frontend-e2e`** si cambia una pantalla (sin los tests del backend). `just ci` (los tres) solo cuando también cambia `backend/`.
- Con RTK, `pnpm lint` se reescribe a eslint: usar las recetas de `just` o `pnpm run lint`.
- TypeScript fijado en 5.x: openapi-typescript aún no funciona con TypeScript 7 (sin API de JS). Se sube cuando lo soporte.

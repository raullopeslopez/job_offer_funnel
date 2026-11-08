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
├── layout/          # navegación lateral; navItems.ts lleva una entrada por pantalla
├── pages/           # una carpeta o fichero por pantalla
└── test/            # setup de Vitest y servidor MSW
```

## Reglas

- **La API, solo a través de `api` (`src/api/client.ts`)**, con las rutas y tipos de `schema.d.ts`. Nada de `fetch` directo ni tipos de la API escritos a mano.
- Si cambia la API: `just openapi` regenera `openapi.json` y los tipos. `just fe-check` falla si `schema.d.ts` no está al día.
- **Sin reglas de negocio en el cliente**: validan la API y sus 422; el formulario los muestra en su campo (`setError`).
- Estilos con el tema y `sx`; ningún color ni tamaño suelto fuera de `theme.ts`.
- Textos de la app en inglés, como el resto del producto.
- Cada pantalla añade su ruta en `router.tsx` y su entrada en `layout/navItems.ts`.

## Tests

- Vitest + Testing Library + MSW, en `*.test.tsx` junto al componente. AAA con comentarios `// Arrange`, `// Act`, `// Assert`; casos que solo cambian en datos, con `it.each`.
- Buscar por rol, etiqueta o texto visible, nunca por clases ni `data-testid` salvo que no haya otra forma.
- MSW con `onUnhandledFrame: "error"`: cada test declara con `server.use` las peticiones que espera. `localStorage` se limpia tras cada test.
- E2E (Playwright + playwright-bdd sobre `specs/ui/`): entra con la primera pantalla (`inbox`).

## Herramientas

- `just fe-dev` (con `just dev` para la API) · `just fe-fmt` · `just fe-check` (Biome, `tsc`, deriva de tipos) · `just fe-test` · `just ci-frontend`.
- Con RTK, `pnpm lint` se reescribe a eslint: usar las recetas de `just` o `pnpm run lint`.
- TypeScript fijado en 5.x: openapi-typescript aún no funciona con TypeScript 7 (sin API de JS). Se sube cuando lo soporte.

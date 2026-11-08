---
name: sdd-feature
description: Ciclo Spec-Driven Development para implementar una feature del backend de job_offer_funnel, desde la spec Gherkin hasta el merge. Usar cuando el usuario pida implementar, añadir o cambiar una funcionalidad o comportamiento.
---

# Ciclo SDD por feature

No se escribe código de producción sin una spec aprobada. Si cambia el comportamiento, primero cambia la spec.

## 1. Spec
1. Crear la rama `feat/<slug>` (o `fix/<slug>`).
2. Leer `docs/funnel.md` y `docs/glossary.md`.
3. Escribir `specs/<modulo>/<nombre>.feature` (reglas en `.claude/rules/specs.md`).
4. Commit: `test(spec): <descripción>`.
5. **Parar.** Presentar la spec al usuario y esperar su aprobación. No continuar sin ella.

## 2. Contrato
6. Schemas Pydantic (`XCreate`/`XUpdate`/`XRead`) y firmas del router, sin lógica.
7. `just openapi` y mostrar el diff de `openapi.json`.
8. **Parar.** Esperar la aprobación del contrato.

## 3. Rojo
9. Steps BDD en `backend/tests/bdd/`. Ejecutar `just test-bdd` y confirmar que **fallan por el motivo esperado** (no por errores de import o de setup).
   - Si los `Given` necesitan estado persistido que ningún endpoint puede crear todavía: adelantar aquí `models.py` + migración y usar factories (`tests/support/factories.py`). Así el rojo es "endpoint no implementado" y no "la tabla no existe".
10. Commit: `test(<modulo>): add failing steps for <feature>`.

## 4. Verde
11. Implementar en este orden, lo mínimo para pasar:
    - `domain.py` + tests unit (solo módulos de dominio).
    - `models.py`, importado en `migrations/env.py` (si no, autogenerate no ve las tablas) + migración (`just migration "msg"`, revisar el fichero generado).
    - `repository.py` → `service.py` → `router.py`, incluido en el router `api` de `main.py` (prefijo `/api/v1`, protegido con token).
    - Si el módulo es nuevo: añadir su contrato de capas en `[tool.importlinter]` de `backend/pyproject.toml`.
12. Refactorizar con los tests en verde.
13. `just ci` en verde. Mostrar el comando y su salida como evidencia.
14. Commit: `feat(<modulo>): <descripción>`.

## 5. Cierre
15. Añadir los cambios de la feature a `[Unreleased]` en `CHANGELOG.md`. Comprobar la Definition of Done del `CLAUDE.md`.
16. Si se cierra un hito, actualizar "Estado actual" en el `CLAUDE.md`.
17. Push de la rama, `gh pr create` hacia `main` (resumen + evidencia) y `gh pr checks`. **El merge lo hace el usuario**: no mergear nunca.

## Reglas durante el ciclo
- Ante la duda sobre el comportamiento: preguntar, no inventar. La spec manda.
- La solución más simple que cumpla la spec. Nada que la spec no pida.
- Si tras dos intentos algo sigue fallando, parar y explicar el bloqueo en vez de un tercer intento a ciegas.

---
paths:
  - "Justfile"
  - "docker-compose.yml"
  - ".github/**"
  - ".pre-commit-config.yaml"
  - "backend/pyproject.toml"
---

# Entorno de desarrollo

## Windows

- Docker Desktop debe estar arrancado para la BD y los tests con testcontainers.
- La ruta del home lleva tilde (`C:\Users\Raúl`): si fallan volúmenes, testcontainers o herramientas con rutas, sospechar de esto primero (usar `UV_CACHE_DIR`/`TMP` con rutas ASCII).
- Justfile: `set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]`.

## Recetas del Justfile (objetivo)

Cuando exista el Justfile, `just --list` es la fuente de verdad y esta lista se elimina.

- **Setup**: `setup` (uv sync + pre-commit install + db-up + migrate).
- **BD**: `db-up`, `db-down`, `db-reset` (volumen + migrate), `db-shell` (psql).
- **Migraciones**: `migrate`, `migration "msg"` (autogenerate), `downgrade` (-1).
- **Ejecutar**: `dev` (uvicorn --reload), `worker` (cuando exista el primer job).
- **Calidad**: `fmt` (ruff format + fix), `lint` (sin modificar), `typecheck` (mypy), `check` (lint + typecheck + import-linter).
- **Tests**: `test *args` (-n auto), `test-unit` (en serie), `test-integration`, `test-bdd`, `test-migrations`, `test-contract`, `test-one "expr"` (sin xdist), `cov`.
- **SDD**: `spec modulo nombre` (plantilla .feature), `openapi` (exporta openapi.json).
- **CI**: `ci` (lint + typecheck + test). GitHub Actions solo llama a `just ci`.

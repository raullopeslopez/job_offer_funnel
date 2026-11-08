---
paths:
  - "Justfile"
  - "docker-compose.yml"
  - ".env.example"
  - ".github/**"
  - ".pre-commit-config.yaml"
  - ".claude/hooks/**"
  - "backend/pyproject.toml"
---

# Entorno de desarrollo

- Recetas: `just --list` es la fuente de verdad. El Justfile carga `.env` de la raíz (`dotenv-load`) y ejecuta en `backend/` (`working-directory`); compose se invoca con `-f ../docker-compose.yml`.
- Recetas compatibles con sh (CI) y PowerShell 5.1 (Windows): un comando por línea y sin `&&`. Cada línea se ejecuta aparte, y just para en el primer fallo.
- Postgres local en el puerto `5434` (configurable con `POSTGRES_PORT`), para no chocar con otros proyectos (ya hay uno en `5433`).
- Docker Desktop debe estar arrancado para `just db-up` y para los tests con BD.
- La ruta del home lleva tilde (`C:\Users\Raúl`): los scripts que lean stdin o rutas deben decodificar en UTF-8 de forma explícita (ver `.claude/hooks/`). Si algo falla con rutas, sospechar de esto primero.
- CI (`.github/workflows/backend.yml`): instala just con `uv tool install rust-just` y ejecuta `just ci`. No duplicar pasos del Justfile en el workflow.
- Hooks de Claude Code (`.claude/hooks/`): `format_python.py` (PostToolUse, solo `ruff format`) y `check_on_stop.py` (Stop: `just check` si hay cambios en `backend/`, bloquea si falla).
- pre-commit: ruff y mypy vía `uv run`; ruff con `--project backend`, porque recibe rutas relativas a la raíz.
- **Uso diario**: `just up` levanta la API (perfil `app` de compose, puerto `8080`) y la BD; migra al arrancar. `just dev` y `just db-up` solo levantan la BD. Ambos usan el mismo volumen `pgdata`: son datos reales, y `just db-reset` los borra.

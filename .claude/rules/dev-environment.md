---
paths:
  - "Justfile"
  - "docker-compose.yml"
  - ".env.example"
  - ".github/**"
  - ".pre-commit-config.yaml"
  - ".claude/hooks/**"
  - "backend/pyproject.toml"
  - "frontend/package.json"
  - "frontend/Dockerfile"
  - "frontend/nginx.conf"
---

# Entorno de desarrollo

- Recetas: `just --list` es la fuente de verdad. El Justfile carga `.env` de la raíz (`dotenv-load`) y ejecuta en `backend/` (`working-directory`); compose se invoca con `-f ../docker-compose.yml`. Las recetas `frontend-*` llevan `[working-directory("../frontend")]`.
- Recetas compatibles con sh (CI) y PowerShell 5.1 (Windows): un comando por línea y sin `&&`. Cada línea se ejecuta aparte, y just para en el primer fallo.
- Postgres local en el puerto `5434` (configurable con `POSTGRES_PORT`), para no chocar con otros proyectos (ya hay uno en `5433`).
- Docker Desktop debe estar arrancado para `just db-up` y para los tests con BD.
- La ruta del home lleva tilde (`C:\Users\Raúl`): los scripts que lean stdin o rutas deben decodificar en UTF-8 de forma explícita (ver `.claude/hooks/`). Si algo falla con rutas, sospechar de esto primero.
- CI: dos workflows con filtro de rutas. `backend.yml` ejecuta `just backend-ci`; `frontend.yml` (Node de `frontend/.node-version`, pnpm de `packageManager`) ejecuta `just frontend-install` y `just frontend-ci`. Ambos instalan just con `uv tool install rust-just`. `just ci` ejecuta los dos. No duplicar pasos del Justfile en los workflows.
- Hooks de Claude Code (`.claude/hooks/`): `format_python.py` (PostToolUse, solo `ruff format`) y `check_on_stop.py` (Stop: `just check` si hay cambios en `backend/` y `just frontend-check` si los hay en `frontend/`; bloquea si falla).
- pre-commit: ruff y mypy vía `uv run`; ruff con `--project backend`, porque recibe rutas relativas a la raíz. Biome con `pnpm --dir frontend exec`.
- **Uso diario**: `just up` levanta la app web (servicio `web`, nginx, puerto `8081`), la API (perfil `app` de compose, puerto `8080`) y la BD; migra al arrancar. nginx reenvía `/api` a la API: mismo origen, sin CORS. `just dev` y `just db-up` solo levantan la BD. Ambos usan el mismo volumen `pgdata`: son datos reales. `just db-backup` guarda una copia en `backups/` (ignorado por git) y `just db-restore <fichero>` la recupera; `db-reset` y `db-restore` piden confirmación (`just --yes` la salta, p. ej. en scripts).
- **Deploy** (Render + Neon, `render.yaml`): `job-offer-funnel-api` (Docker, plan free, Frankfurt; migra al arrancar) y `job-offer-funnel-web` (static site, reescribe `/api/*` a la URL de la API: mismo origen, sin CORS). BD en Neon (proyecto `job-offer-funnel`, `aws-eu-central-1`), endpoint directo (sin `-pooler`: PgBouncer en modo transacción rompe los prepared statements de asyncpg) y `?ssl=require` en vez de `sslmode`/`channel_binding`, que asyncpg no entiende. `DATABASE_URL` se pone a mano en Render; `AUTH_TOKEN` lo genera Render (verlo en el dashboard). Plan free: la API duerme a los 15 min y tarda ~1 min en despertar. Si Render no da la URL `job-offer-funnel-api.onrender.com` (nombre ocupado), corregir el rewrite.

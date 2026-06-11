# Memoria

BI platform analyzing the gender gap in the hierarchy of paper authorship
(1st, penultimate, last author position, etc.). Thesis project, Computer Science.

## Architecture

Data flows left to right:

    CSVs (raw)
      └─> etl/load_postgres.py          # ingest to OLTP
            └─> PostgreSQL              # normalized source of truth
                  └─> etl/load_clickhouse.py   # transform + load
                        └─> ClickHouse         # analytical warehouse
                              └─> Apache Superset  # dashboards / web UI

- **PostgreSQL** is the normalized source of truth. Populated from CSVs.
- **ClickHouse** is the analytical warehouse. Read by Superset. Do NOT connect Superset to PostgreSQL.
- **Apache Superset** is the web UI. Dashboards read from ClickHouse only.

## Repo layout

- `etl/` — Python scripts (CSV → Postgres, Postgres → ClickHouse)
- `db/` — DDL / migrations for Postgres and ClickHouse
- `superset/` — exported dashboards, config assets
- `data/` — CSVs (gitignored, large/raw)
- `docker-compose.yml` — Postgres + ClickHouse for local dev (Superset is added in EPIC-03)
- `requirements.txt` — Python deps
- `.env.example` — connection strings, credentials

## Workflow (GitFlow + Kanban)

### Estructura de épicas y tasks
- **Épica**: `EPIC-NN` (2 dígitos). Catálogo actual:
  - `EPIC-01`: ETL + Postgres (OLTP, fuente de verdad)
  - `EPIC-02`: ETL + ClickHouse (DW analítico)
  - `EPIC-03`: Apache Superset (BI)
- **Task**: `TASK-NN-NNN` (épica + 3 dígitos secuenciales dentro de la épica). Catálogo vivo en `KANBAN.md`.

### Branches
| Tipo | Patrón | Origen → Destino |
|------|--------|------------------|
| Producción | `main` | recibe merges desde `develop` al cerrar una épica |
| Integración | `develop` | recibe feature branches; branch de trabajo por defecto |
| Feature | `feature/EPIC-NN-TASK-NNN-kebab-slug` | `develop` → `develop` (squash merge) |
| Hotfix | `hotfix/short-slug` | `main` → `main` + cherry-pick a `develop` |
| Release | `release/vMAJOR.MINOR.PATCH` | `develop` → `main` + tag |

Slug: kebab-case, ≤ 50 chars, sin acentos, refleja QUÉ hace la task (no el épica). Ejemplos válidos: `etl-load-postgres`, `db-schema-ddl`. Inválidos: `TASK-007`, `cosa nueva`.

### Commits (Conventional Commits)
Formato: `<type>(<scope>): <subject>`

| Type | Cuándo |
|------|--------|
| `feat` | Nueva funcionalidad (código nuevo) |
| `fix` | Corrección de bug |
| `chore` | Mantenimiento / bootstrap / configs |
| `docs` | Solo documentación |
| `refactor` | Cambio de código sin feature ni fix |
| `test` | Agregar o corregir tests |
| `build` | Dependencias / build |
| `ci` | CI/CD |

Scope sugerido: `db`, `etl`, `docker`, `docs`, `kanban`, `infra`, `gitignore`.
Subject: imperativo en presente, minúscula, sin punto final, ≤ 72 chars.
Prefijo opcional con ID de task: `[TASK-01-007] feat(etl): add load_postgres.py`.

Ejemplos válidos:
```
feat(etl): add SJR loader script
feat(db): add DDL for 12 tables
docs(arquitectura): simplify Investigador schema
chore: bootstrap repo with AGENTS.md and ARQUITECTURA.md
[TASK-01-002] feat(db): add Paper, Journal, Investigador tables
fix(etl): map fist→first in Posicion.PosicionInteres
```

### Pull requests
Título: `[EPIC-NN] [TASK-NN-NNN] <descripción-corta>`. Cuerpo: descripción del cambio, link a task del kanban, screenshots si aplica.

### Merge strategy
- Feature → develop: **squash merge** (1 commit limpio por task).
- develop → main al cerrar una épica: **merge commit** (preserva historial de la épica).
- Mensaje del merge a main: `[EPIC-NN] close epic: <nombre-épicica>`.

### Flujo por task
1. Sincronizar develop: `git switch develop && git pull`
2. Crear branch desde develop: `git switch -c feature/EPIC-01-TASK-001-data-folder-structure`
3. Commits siguiendo Conventional Commits.
4. Push + PR a `develop` con título `[EPIC-01] [TASK-01-001] ...`.
5. Squash merge a `develop` cuando se aprueba.
6. Actualizar `KANBAN.md` marcando la task como `done` en el mismo PR.

### Estado del kanban
Vive en `KANBAN.md` (raíz). Se actualiza junto con el PR que cierra la task. No requiere herramienta externa.

## Prerequisites

- Python 3.11+ with `venv`
- Docker + Docker Compose v2
- ~4 GB RAM free (ClickHouse + Superset are hungry)

## Setup

    python -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env             # then fill in
    docker compose up -d             # Postgres, ClickHouse, Superset

## Common commands

| Task                       | Command                                                       |
|----------------------------|---------------------------------------------------------------|
| Activate venv              | `source .venv/bin/activate` (Win: `.venv\Scripts\activate`)   |
| Install deps               | `pip install -r requirements.txt`                             |
| Update requirements.txt    | `pip freeze > requirements.txt` (after installing new deps)   |
| Start services             | `docker compose up -d`                                        |
| Stop services              | `docker compose down`                                         |
| Reset warehouse data       | `docker compose down -v && docker compose up -d`              |
| Load CSVs → Postgres       | `python -m etl.load_postgres`                                 |
| Load OpenAlex publishers   | `python -m etl.load_postgres_publishers`                      |
| Load SJR factors           | `python -m etl.load_postgres_sjr`                             |
| Verify Postgres            | `python -m etl.verify`                                        |
| Transform → ClickHouse     | `python -m etl.load_clickhouse`                               |
| Open Superset              | http://localhost:8088                                         |

## Conventions

- **DB connections** from env vars (`POSTGRES_*`, `CLICKHOUSE_*`); never hardcode.
- **Idempotent ETL**: re-running a load script must not duplicate rows. Use upsert / `INSERT ... ON CONFLICT`, or truncate-and-reload on staging tables.
- **CSVs are the source of truth** for raw data. Postgres is rebuilt from CSVs, not the reverse.
- **Schema changes** go in `db/`; never mutate a running DB manually.
- **ClickHouse tables** declare `ORDER BY` on the column you'll filter on (e.g., `year`, `author_position`).

## Gotchas

- Superset connects to **ClickHouse**, not Postgres. If a dashboard is empty, check the ClickHouse connection first.
- ClickHouse does not enforce uniqueness the way Postgres does. Design aggregations accordingly.
- Large CSV loads: prefer `COPY` (psycopg `copy_expert`) over row-by-row `INSERT`.
- `data/` and `.env` are gitignored. CSVs come from the original source — do not commit them.
- Run ETL scripts as modules: `python -m etl.<script>` (not `python etl/<script>.py`). The `etl/` package needs `__init__.py` and `-m` adds the project root to `sys.path` so internal imports resolve.

## When this file needs updating

- New ETL script added → add a row to "Common commands".
- New service in `docker-compose.yml` → update "Prerequisites" and "Common commands".
- New convention agreed (branch naming, commit style, etc.) → add under "Conventions".
- A gotcha bit you → add under "Gotchas".

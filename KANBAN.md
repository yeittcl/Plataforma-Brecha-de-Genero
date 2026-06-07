# Kanban — Memoria

Catálogo vivo de épicas y tasks. Actualizar el estado (`pending` / `in-progress` / `done`)
en el mismo PR que cierra cada task.

## EPIC-01 — ETL + Postgres (OLTP, fuente de verdad)

**Status**: pending

- [x] **TASK-01-001** — Crear estructura de carpetas y mover CSVs ganadores a `data/raw/` y SJR a `data/external/sjr/`
- [x] **TASK-01-002** — Crear `db/01_schema.sql` con DDL de las 12 tablas + constraints
- [ ] **TASK-01-003** — Crear `db/02_seed_static.sql` (Region, Pais, Area, Posicion)
- [ ] **TASK-01-004** — Crear `db/03_seed_categories.sql` (36 pares Area-Categoria)
- [ ] **TASK-01-005** — Crear `requirements.txt` + `docker-compose.yml` (Postgres + ClickHouse) + `.env.example` + `.gitignore`
- [ ] **TASK-01-006** — Crear `etl/common.py` (env vars, conexión DB, mapeo `fist→first`, normalizador de países)
- [ ] **TASK-01-007** — Implementar `etl/load_postgres.py` (DF1 + DF2 + PubMed + DBLP → Postgres)
- [ ] **TASK-01-008** — Implementar `etl/load_postgres_publishers.py` (OpenAlex `/publishers` + `/sources`)
- [ ] **TASK-01-009** — Implementar `etl/load_postgres_sjr.py` (Scimago SJR 1999-2025 → `Factor_Impacto`)
- [ ] **TASK-01-010** — Verificación: queries de conteo, `EXPLAIN`, smoke test de idempotencia

## EPIC-02 — ETL + ClickHouse (DW analítico)

**Status**: pending

- [ ] **TASK-02-001** — Crear DDL de ClickHouse (`db/clickhouse_schema.sql`)
- [ ] **TASK-02-002** — Implementar `etl/load_clickhouse.py` (Postgres → ClickHouse)
- [ ] **TASK-02-003** — Verificación: counts, sample queries OLAP

## EPIC-03 — Apache Superset (BI)

**Status**: pending

- [ ] **TASK-03-001** — `docker-compose.yml` con Superset
- [ ] **TASK-03-002** — Conexión ClickHouse en Superset
- [ ] **TASK-03-003** — Datasets y dimensiones
- [ ] **TASK-03-004** — Dashboards

## Leyenda
- `[ ]` pending
- `[~]` in-progress
- `[x]` done

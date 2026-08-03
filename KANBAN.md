# Kanban — Memoria

Catálogo vivo de épicas y tasks. Actualizar el estado (`pending` / `in-progress` / `done`)
en el mismo PR que cierra cada task.

## EPIC-01 — ETL + Postgres (OLTP, fuente de verdad)

**Status**: done (released as v0.1.0)

- [x] **TASK-01-001** — Crear estructura de carpetas y mover CSVs ganadores a `data/raw/` y SJR a `data/external/sjr/`
- [x] **TASK-01-002** — Crear `db/01_schema.sql` con DDL de las 12 tablas + constraints
- [x] **TASK-01-003** — Crear `db/02_seed_static.sql` (Region, Pais, Area, Posicion)
- [x] **TASK-01-004** — Crear `db/03_seed_categories.sql` (36 pares Area-Categoria)
- [x] **TASK-01-005** — Crear `requirements.txt` + `docker-compose.yml` (Postgres + ClickHouse) + `.env.example` + `.gitignore`
- [x] **TASK-01-006** — Crear `etl/common.py` (env vars, conexión DB, mapeo `fist→first`, normalizador de países)
- [x] **TASK-01-007** — Implementar `etl/load_postgres.py` (DF1 + DF2 + PubMed + DBLP → Postgres)
- [x] **TASK-01-008** — Implementar `etl/load_postgres_publishers.py` (OpenAlex `/publishers` + `/sources`)
- [x] **TASK-01-009** — Implementar `etl/load_postgres_sjr.py` (Scimago SJR 1999-2025 → `Factor_Impacto`)
- [x] **TASK-01-010** — Verificación: queries de conteo, `EXPLAIN`, smoke test de idempotencia

## EPIC-02 — ETL + ClickHouse (DW analítico)

**Status**: done (released as v0.2.0)

- [x] **TASK-02-001** — Crear DDL de ClickHouse (`db/clickhouse_schema.sql`)
- [x] **TASK-02-002** — Implementar `etl/load_clickhouse.py` (Postgres → ClickHouse)
- [x] **TASK-02-003** — Verificación: counts, sample queries OLAP

## EPIC-03 — Apache Superset (BI)

**Status**: in-progress

- [x] **TASK-03-001** — `docker-compose.yml` con Superset + Nginx (landing en :8080, Superset en :8088)
- [x] **TASK-03-002** — Datasets: 6 datasets (5 dims + Fact_Paper) + 14 métricas virtuales en `Fact_Paper`. Round-trip YAML probado. Idempotente via `init_datasets.py`.
- [x] **TASK-03-003** — Dashboards (manuales via UI, 6 dashboards temáticos)
- [x] **TASK-03-004** — Infra Celery + Redis para SQL Lab (redis 7, superset-worker). Workaround para incompat 3.1.3+clickhouse-sqlalchemy 0.2.7: `allow_run_async=False` en la DB ClickHouse (sync only). SQL Lab funciona end-to-end. Tambien incluye: Nginx routing (Superset en raiz, landing en /landing/), proxy Host fix, DASHBOARD_RBAC, LOGO_TARGET_PATH, landing page.
- [x] **TASK-03-005** — Landing page + i18n español
- [ ] **TASK-03-006** — Verificación + cierre EPIC-03 (README)

## EPIC-04 — Testing

**Status**: in-progress

- [x] **TASK-04-001** — Unit tests: 49 tests para funciones puras (normalize_position, normalize_country, truncate, strip_accents, _quote_col, _extract_position_from_id, parse_sjr_value, find_journal_id, SQL helper, DATASETS, METRICS, DASHBOARDS)
- [x] **TASK-04-002** — Integration tests: schema validation (Postgres + ClickHouse DDL), data quality
- [x] **TASK-04-003** — E2E tests: ETL module importability (syntax check)

## Leyenda
- `[ ]` pending
- `[~]` in-progress
- `[x]` done

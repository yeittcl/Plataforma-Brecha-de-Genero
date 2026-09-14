# Memoria — Plataforma de Análisis de la Brecha de Género en Autoría Científica

Plataforma BI que analiza la brecha de género en la jerarquía de autoría de papers científicos (primera autora, última autora, investigadora principal). Proyecto de tesis en Ciencias de la Computación.

## Arquitectura

```
CSVs (raw)
  └─> etl/load_postgres.py           # ingest to OLTP
        └─> PostgreSQL                # normalized source of truth
              └─> etl/load_clickhouse.py  # transform + load
                    └─> ClickHouse    # analytical warehouse
                          └─> Apache Superset  # dashboards / web UI
```

- **PostgreSQL**: fuente de verdad normalizada. Poblada desde CSVs.
- **ClickHouse**: almacén analítico. Leído por Superset. No conectar Superset a PostgreSQL.
- **Apache Superset**: interfaz web. Dashboards leen desde ClickHouse.

## Requisitos

- Python 3.11+ con `venv`
- Docker + Docker Compose v2
- ~4 GB RAM libre (ClickHouse + Superset)
- ~5 GB RAM cuando Superset + Nginx están corriendo

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # completar credenciales
docker compose up -d             # Postgres, ClickHouse, Superset
```

## Comandos comunes

| Tarea | Comando |
|-------|---------|
| Activar venv | `source .venv/bin/activate` (Win: `.venv\Scripts\activate`) |
| Instalar dependencias | `pip install -r requirements.txt` |
| Actualizar requirements.txt | `pip freeze > requirements.txt` |
| Iniciar servicios | `docker compose up -d` |
| Detener servicios | `docker compose down` |
| Resetear datos | `docker compose down -v && docker compose up -d` |
| Cargar CSVs → Postgres | `python -m etl.load_postgres` |
| Cargar publishers (OpenAlex) | `python -m etl.load_postgres_publishers` |
| Cargar factores SJR | `python -m etl.load_postgres_sjr` |
| Verificar Postgres | `python -m etl.verify` |
| Transformar → ClickHouse | `python -m etl.load_clickhouse` |
| Abrir landing | http://localhost:8080 |
| Abrir Superset (admin) | http://localhost:8088 |

## Estructura del repo

```
├── data/                    # CSVs (gitignored, raw/external)
├── db/
│   ├── 01_schema.sql        # DDL Postgres (12 tablas)
│   ├── 02_seed_static.sql   # Seeds: Region, Pais, Area, Posicion
│   ├── 03_seed_categories.sql # 36 pares Area-Categoria
│   └── clickhouse_schema.sql # DDL ClickHouse (6 tablas)
├── etl/
│   ├── common.py            # Env vars, conexiones, normalización
│   ├── load_postgres.py     # CSV → Postgres (DF1, DF2, PubMed, DBLP)
│   ├── load_postgres_publishers.py  # OpenAlex publishers
│   ├── load_postgres_sjr.py  # SJR → Factor_Impacto
│   ├── load_clickhouse.py   # Postgres → ClickHouse
│   ├── verify.py            # Verificación de integridad
│   └── sources/             # Parseo de fuentes individuales
├── superset/
│   ├── config/              # Scripts de inicialización
│   ├── dashboards/          # Export YAML de dashboards
│   ├── datasets/            # Export YAML de datasets
│   ├── Dockerfile           # Imagen personalizada de Superset
│   └── requirements-local.txt
├── nginx/
│   ├── default.conf         # Routing: landing en /, Superset en /superset
│   └── html/landing/        # Landing page estática
├── tests/
│   ├── unit/                # 49 tests de funciones puras
│   ├── integration/         # 9 tests de schema DDL
│   └── e2e/                 # 3 tests de importabilidad ETL
├── docker-compose.yml       # 6 servicios
├── requirements.txt         # Dependencias Python
└── .env.example             # Template de credenciales
```

## Datos

Los CSVs provienen de fuentes originales (OpenAlex, Scimago, DBLP, PubMed) y no se committean al repositorio. Ver `data/` para la estructura de carpetas.

### Fuentes utilizadas

| Fuente | Contenido | Archivo |
|--------|-----------|---------|
| OpenAlex | Papers, autores, afiliaciones | `data/raw/` |
| Scimago (SJR) | Factor de impacto por journal y año | `data/external/sjr/` |
| DBLP | Metadatos de Computer Science | `data/raw/` |
| PubMed | Metadatos biomédicos | `data/raw/` |

## Dashboards

La plataforma incluye 5 dashboards temáticos:

1. **Resumen General** — KPIs principales y distribución global
2. **Brecha de Género por Área** — Comparación entre áreas científicas (BIO, CHEM, CS, EARTH, PHYS)
3. **Tendencia Temporal** — Evolución de la brecha a lo largo del tiempo
4. **Brecha de Género Geográfica** — Diferencias por país/región
5. **Brecha de Género por Revista-Editorial** — Análisis por journals y editoriales

Cada dashboard incluye narrativa explicativa (Markdown) que guía al usuario hacia los insights clave.

## Tests

```bash
# Todos los tests
python -m pytest tests/ -v

# Solo unit tests
python -m pytest tests/unit/ -v

# Solo integration
python -m pytest tests/integration/ -v

# Solo E2E
python -m pytest tests/e2e/ -v
```

## Convenciones

- **Commits**: Conventional Commits (`feat(scope): subject`)
- **Branches**: GitFlow (`feature/EPIC-NN-TASK-NNN-kebab-slug`)
- **DB connections**: desde env vars (`POSTGRES_*`, `CLICKHOUSE_*`); nunca hardcodear
- **ETL idempotente**: re-ejecutar no duplica filas (usar `INSERT ... ON CONFLICT`)
- **CSVs son fuente de verdad**: Postgres se reconstruye desde CSVs

## License

Proyecto de tesis — Universidad de Concepción, 2026.

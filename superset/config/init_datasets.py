"""Idempotent: create the 6 Superset datasets for the Memoria DW.

Run via:
    docker run --rm --network=memoria_default \
        -v "$PWD/superset/config:/app/cfg:ro" \
        -v "$PWD/superset/config/superset_config.py:/app/pythonpath/superset_config.py:ro" \
        -v "memoria_superset_data:/app/superset_home" \
        -e CLICKHOUSE_HOST=clickhouse -e CLICKHOUSE_HTTP_PORT=8123 \
        -e CLICKHOUSE_DB=memoria -e CLICKHOUSE_USER=memoria -e CLICKHOUSE_PASSWORD=password \
        memoria-superset:latest \
        python3 -c "import importlib.util; s=importlib.util.spec_from_file_location('m','/app/cfg/init_datasets.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.main()"
"""
import importlib.util
import os
import sys

os.environ.setdefault("SUPERSET_CONFIG_PATH", "/app/pythonpath/superset_config.py")


DATASETS = [
    {
        "table_name": "Dim_Geografica",
        "schema": "memoria",
        "description": "Dim Geografica: paises y regiones",
        "columns": [
            ("IdGeo", False, True),
            ("NombrePais", True, True),
            ("NombreRegion", True, True),
        ],
    },
    {
        "table_name": "Dim_Tiempo",
        "schema": "memoria",
        "description": "Dim Tiempo: anios y decadas",
        "columns": [
            ("IdTiempo", False, True),
            ("Año", False, False),
            ("Decada", True, True),
            ("Siglo", True, True),
            ("Hito", True, True),
        ],
    },
    {
        "table_name": "Dim_Area",
        "schema": "memoria",
        "description": "Dim Area: areas y categorias (rows duplicadas por IdArea)",
        "columns": [
            ("IdArea", False, True),
            ("NombreArea", True, True),
            ("NombreCategoria", True, True),
        ],
    },
    {
        "table_name": "Dim_Journal",
        "schema": "memoria",
        "description": "Dim Journal: revistas y editoriales",
        "columns": [
            ("IdJournal", False, True),
            ("NombreJournal", True, True),
            ("NombreEditorial", True, True),
        ],
    },
    {
        "table_name": "Dim_FactorImpacto",
        "schema": "memoria",
        "description": "Dim FactorImpacto: SJR por journal y anio",
        "columns": [
            ("IdFactorImpacto", False, True),
            ("IdJournal", False, True),
            ("Año", False, False),
            ("SJR", True, True),
        ],
    },
    {
        "table_name": "Fact_Paper",
        "schema": "memoria",
        "description": "Fact Paper: 1 fila por paper, con flags de genero",
        "columns": [
            ("IdPaper", False, False),
            ("IdTiempo", False, True),
            ("IdGeo", False, True),
            ("IdJournal", False, True),
            ("IdArea", False, True),
            ("Mujer_primera", True, True),
            ("Mujer_penult", True, True),
            ("Mujer_ult", True, True),
            ("Hay_mujeres", True, True),
            ("Mujer_Autora", True, True),
            ("N_mujeres", True, True),
            ("N_autores", True, True),
        ],
        "metrics": [
            ("count", "COUNT(*)", "number"),
            ("n_mujer_primera", "SUM(Mujer_primera)", "number"),
            ("n_mujer_penult", "SUM(Mujer_penult)", "number"),
            ("n_mujer_ult", "SUM(Mujer_ult)", "number"),
            ("n_con_mujeres", "SUM(Hay_mujeres)", "number"),
            ("n_unipersonal_mujer", "SUM(Mujer_Autora)", "number"),
            ("pct_mujer_primera", "SUM(Mujer_primera) * 100.0 / COUNT(*)", "number"),
            ("pct_mujer_penult", "SUM(Mujer_penult) * 100.0 / COUNT(*)", "number"),
            ("pct_mujer_ult", "SUM(Mujer_ult) * 100.0 / COUNT(*)", "number"),
            ("pct_con_mujeres", "SUM(Hay_mujeres) * 100.0 / COUNT(*)", "number"),
            ("pct_unipersonal_mujer", "SUM(Mujer_Autora) * 100.0 / COUNT(*)", "number"),
            ("avg_n_mujeres", "AVG(N_mujeres)", "number"),
            ("avg_n_autores", "AVG(N_autores)", "number"),
            ("pct_unipersonal", "SUM(IF(N_autores = 1, 1, 0)) * 100.0 / COUNT(*)", "number"),
        ],
    },
]


def main():
    from superset.app import create_app
    from sqlalchemy import create_engine, inspect

    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.core import Database
        from superset.connectors.sqla.models import SqlaTable, TableColumn, SqlMetric

        ch_db = db.session.query(Database).filter_by(database_name="ClickHouse - Memoria").first()
        if not ch_db:
            print("[datasets] No ClickHouse database connection found")
            sys.exit(1)

        engine = create_engine(ch_db.sqlalchemy_uri)
        insp = inspect(engine)
        type_map = {
            "UInt64": "BIGINT",
            "UInt32": "INTEGER",
            "UInt16": "INTEGER",
            "UInt8": "TINYINT",
            "Int64": "BIGINT",
            "Int32": "INTEGER",
            "Int16": "SMALLINT",
            "Int8": "TINYINT",
            "Float64": "FLOAT",
            "Float32": "FLOAT",
            "String": "VARCHAR",
        }

        for ds_def in DATASETS:
            tbl = ds_def["table_name"]
            existing = (
                db.session.query(SqlaTable)
                .filter_by(database_id=ch_db.id, table_name=tbl)
                .first()
            )
            if existing:
                print(f"[datasets] {tbl} already exists, skipping")
                continue

            ch_cols = insp.get_columns(tbl, schema="memoria")
            ch_col_types = {
                c["name"]: type_map.get(str(c["type"]).split("(")[0], "VARCHAR")
                for c in ch_cols
            }

            ds = SqlaTable(
                table_name=tbl,
                database_id=ch_db.id,
                schema=ds_def["schema"],
                description=ds_def.get("description", ""),
            )
            ds.sql = None
            db.session.add(ds)
            db.session.flush()

            for col_name, groupby, filterable in ds_def["columns"]:
                tc = TableColumn(
                    column_name=col_name,
                    type=ch_col_types.get(col_name, "VARCHAR"),
                    groupby=groupby,
                    filterable=filterable,
                    is_dttm=False,
                    table_id=ds.id,
                )
                db.session.add(tc)

            for mname, mexpr, mtype in ds_def.get("metrics", []):
                sm = SqlMetric(
                    metric_name=mname,
                    expression=mexpr,
                    metric_type=mtype,
                    table_id=ds.id,
                    description=f"Virtual metric: {mname}",
                )
                db.session.add(sm)

            db.session.commit()
            ncols = len(ds_def["columns"])
            nmetrics = len(ds_def.get("metrics", []))
            print(f"[datasets] Created {tbl} (id={ds.id}) with {ncols} cols and {nmetrics} metrics")

        print("[datasets] Done.")


if __name__ == "__main__":
    main()

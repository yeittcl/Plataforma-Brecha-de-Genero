"""Import the 6 datasets from superset/datasets/*.yaml into Superset.

Idempotent: skips datasets that already exist (by table_name+schema+database).

This script is for documentation/reproducibility purposes. The canonical
way to create the datasets is `init_datasets.py` (more robust, no YAML
parse failures, idempotent). Use this import script only if you need to
recreate the datasets from the exported YAMLs.

Run via:
    docker run --rm --network=memoria_default \\
        -v "$PWD/superset/config:/app/cfg:ro" \\
        -v "$PWD/superset/config/superset_config.py:/app/pythonpath/superset_config.py:ro" \\
        -v "$PWD/superset/datasets:/app/yaml:ro" \\
        -v "memoria_superset_data:/app/superset_home" \\
        -e CLICKHOUSE_HOST=clickhouse -e CLICKHOUSE_HTTP_PORT=8123 \\
        -e CLICKHOUSE_DB=memoria -e CLICKHOUSE_USER=memoria -e CLICKHOUSE_PASSWORD=password \\
        memoria-superset:latest \\
        python3 -c "import importlib.util; s=importlib.util.spec_from_file_location('m','/app/cfg/import_datasets.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.main()"
"""
import importlib.util
import os
import sys
from pathlib import Path

os.environ.setdefault("SUPERSET_CONFIG_PATH", "/app/pythonpath/superset_config.py")


def main():
    from superset.app import create_app
    from sqlalchemy import create_engine, inspect

    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.core import Database
        from superset.connectors.sqla.models import SqlaTable, TableColumn, SqlMetric
        import yaml

        ch_db = db.session.query(Database).filter_by(database_name="ClickHouse - Memoria").first()
        if not ch_db:
            print("[import] No ClickHouse database connection found")
            sys.exit(1)

        yaml_dir = Path("/app/yaml")
        if not yaml_dir.exists():
            print(f"[import] No yaml dir at {yaml_dir}")
            sys.exit(1)

        type_map = {
            "BIGINT": "BIGINT", "INTEGER": "INTEGER", "SMALLINT": "SMALLINT",
            "TINYINT": "TINYINT", "FLOAT": "FLOAT", "VARCHAR": "VARCHAR",
        }

        n_created = 0
        n_skipped = 0
        for ypath in sorted(yaml_dir.glob("*.yaml")):
            with open(ypath, "r", encoding="utf-8") as f:
                payload = yaml.safe_load(f)
            tbl = payload.get("table_name")
            schema = payload.get("schema", "memoria")
            if not tbl:
                print(f"[import] WARN: {ypath.name} missing table_name, skipping")
                continue

            existing = (
                db.session.query(SqlaTable)
                .filter_by(database_id=ch_db.id, table_name=tbl, schema=schema)
                .first()
            )
            if existing:
                print(f"[import] {tbl} already exists, skipping")
                n_skipped += 1
                continue

            engine = create_engine(ch_db.sqlalchemy_uri)
            insp = inspect(engine)
            ch_cols = insp.get_columns(tbl, schema=schema)
            ch_col_types = {
                c["name"]: type_map.get(str(c["type"]).split("(")[0], "VARCHAR")
                for c in ch_cols
            }

            ds = SqlaTable(
                table_name=tbl,
                database_id=ch_db.id,
                schema=schema,
                description=payload.get("description", ""),
            )
            ds.sql = payload.get("sql")
            ds.main_dttm_col = payload.get("main_dttm_col")
            ds.default_endpoint = payload.get("default_endpoint")
            ds.offset = payload.get("offset", 0)
            ds.cache_timeout = payload.get("cache_timeout")
            ds.filter_select_enabled = payload.get("filter_select_enabled", True)
            ds.fetch_values_predicate = payload.get("fetch_values_predicate")
            ds.normalize_columns = payload.get("normalize_columns", False)
            ds.always_filter_main_dttm = payload.get("always_filter_main_dttm", False)
            db.session.add(ds)
            db.session.flush()

            for col_def in payload.get("columns", []):
                col_name = col_def["column_name"]
                tc = TableColumn(
                    column_name=col_name,
                    type=ch_col_types.get(col_name, col_def.get("type", "VARCHAR")),
                    groupby=col_def.get("groupby", True),
                    filterable=col_def.get("filterable", True),
                    is_dttm=col_def.get("is_dttm", False),
                    is_active=col_def.get("is_active", True),
                    expression=col_def.get("expression"),
                    description=col_def.get("description"),
                    table_id=ds.id,
                )
                db.session.add(tc)

            for m_def in payload.get("metrics", []):
                sm = SqlMetric(
                    metric_name=m_def["metric_name"],
                    expression=m_def["expression"],
                    metric_type=m_def.get("metric_type", "number"),
                    description=m_def.get("description"),
                    verbose_name=m_def.get("verbose_name"),
                    d3format=m_def.get("d3format"),
                    currency=m_def.get("currency"),
                    warning_text=m_def.get("warning_text"),
                    table_id=ds.id,
                )
                db.session.add(sm)

            db.session.commit()
            print(f"[import] Created {tbl} (id={ds.id}) cols={len(payload.get('columns', []))} metrics={len(payload.get('metrics', []))}")
            n_created += 1

        print(f"[import] Done. Created={n_created} Skipped={n_skipped}")


if __name__ == "__main__":
    main()

"""Idempotent script: ensures ClickHouse database connection exists in Superset."""
import os
import sys

os.environ.setdefault("SUPERSET_CONFIG_PATH", "/app/pythonpath/superset_config.py")


def main():
    ch_host = os.environ["CLICKHOUSE_HOST"]
    ch_port = os.environ["CLICKHOUSE_HTTP_PORT"]
    ch_dbname = os.environ["CLICKHOUSE_DB"]
    ch_user = os.environ["CLICKHOUSE_USER"]
    ch_pass = os.environ["CLICKHOUSE_PASSWORD"]
    ch_uri = f"clickhouse://{ch_user}:{ch_pass}@{ch_host}:{ch_port}/{ch_dbname}"

    from superset.app import create_app

    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.models.core import Database

        existing = db.session.query(Database).filter_by(database_name="ClickHouse - Memoria").first()
        if existing is not None:
            print("[init_db] Database connection already exists, skipping")
            sys.exit(0)

        database = Database(
            database_name="ClickHouse - Memoria",
            sqlalchemy_uri=ch_uri,
            expose_in_sqllab=True,
            allow_ctas=False,
            allow_cvas=False,
            allow_dml=False,
            allow_run_async=True,
        )
        db.session.add(database)
        db.session.commit()
        print(f"[init_db] Created database connection (id={database.id})")
        db.session.remove()


if __name__ == "__main__":
    main()

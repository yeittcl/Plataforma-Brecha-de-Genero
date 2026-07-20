"""Disable async queries for the ClickHouse database.

Workaround for the Superset 3.1.3 + clickhouse-sqlalchemy 0.2.7 incompat
that breaks SQL Lab result processing.
"""
import os
os.environ.setdefault("SUPERSET_CONFIG_PATH", "/app/pythonpath/superset_config.py")

from superset.app import create_app
app = create_app()
with app.app_context():
    from superset.models.core import Database
    from superset import db

    ch = db.session.query(Database).filter_by(database_name="ClickHouse - Memoria").one()
    print(f"Before: allow_run_async = {ch.allow_run_async}")
    ch.allow_run_async = False
    db.session.commit()
    print(f"After:  allow_run_async = {ch.allow_run_async}")

"""Idempotent: create virtual dataset ds_fact_paper_by_country for the world map.

This is a virtual dataset (sql field set) that joins Fact_Paper with Dim_Geografica
and exposes NombrePais as a column. The world_map chart will use it.

Run via:
    docker compose run --rm superset python3 /app/cfg/init_country_ds.py
"""
import os

os.environ.setdefault("SUPERSET_CONFIG_PATH", "/app/pythonpath/superset_config.py")


SQL_QUERY = """
SELECT
    f.IdPaper AS IdPaper,
    f.IdTiempo AS IdTiempo,
    f.IdJournal AS IdJournal,
    f.IdArea AS IdArea,
    g.NombrePais AS NombrePais,
    g.NombreRegion AS NombreRegion,
    f.Mujer_primera AS Mujer_primera,
    f.Mujer_penult AS Mujer_penult,
    f.Mujer_ult AS Mujer_ult,
    f.Hay_mujeres AS Hay_mujeres,
    f.Mujer_Autora AS Mujer_Autora,
    f.N_mujeres AS N_mujeres,
    f.N_autores AS N_autores
FROM Fact_Paper f
INNER JOIN Dim_Geografica g ON g.IdGeo = f.IdGeo
WHERE g.NombrePais != 'Unknown'
"""


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.connectors.sqla.models import SqlaTable, TableColumn, SqlMetric
        from superset import db

        existing = (
            db.session.query(SqlaTable)
            .filter_by(table_name="ds_fact_paper_by_country", schema="memoria")
            .first()
        )
        if existing:
            print("[country_ds] already exists, skipping")
            return

        parent = (
            db.session.query(SqlaTable)
            .filter_by(table_name="Fact_Paper", schema="memoria")
            .first()
        )
        if not parent:
            print("[country_ds] ERROR: Fact_Paper dataset not found")
            return

        ds = SqlaTable(
            table_name="ds_fact_paper_by_country",
            database_id=parent.database_id,
            schema="memoria",
            description="Fact_Paper JOIN Dim_Geografica para mapas (excluye Unknown)",
        )
        ds.sql = SQL_QUERY
        ds.main_dttm_col = None
        ds.is_sqllab_view = True
        db.session.add(ds)
        db.session.flush()

        # Add columns matching the SELECT
        cols = [
            ("IdPaper", False, False),
            ("IdTiempo", False, True),
            ("IdJournal", False, True),
            ("IdArea", False, True),
            ("NombrePais", True, True),
            ("NombreRegion", True, True),
            ("Mujer_primera", True, True),
            ("Mujer_penult", True, True),
            ("Mujer_ult", True, True),
            ("Hay_mujeres", True, True),
            ("Mujer_Autora", True, True),
            ("N_mujeres", True, True),
            ("N_autores", True, True),
        ]
        for col_name, groupby, filterable in cols:
            tc = TableColumn(
                column_name=col_name,
                type="INTEGER" if col_name in ("IdPaper", "IdTiempo", "IdJournal", "IdArea", "N_mujeres", "N_autores", "Mujer_primera", "Mujer_penult", "Mujer_ult", "Hay_mujeres", "Mujer_Autora") else "VARCHAR",
                groupby=groupby,
                filterable=filterable,
                is_dttm=False,
                table_id=ds.id,
            )
            db.session.add(tc)

        # Add metrics
        metrics = [
            ("count", "COUNT(*)", "number"),
            ("n_mujer_primera", "SUM(Mujer_primera)", "number"),
            ("n_mujer_ult", "SUM(Mujer_ult)", "number"),
            ("n_con_mujeres", "SUM(Hay_mujeres)", "number"),
            ("pct_mujer_primera", "SUM(Mujer_primera) * 100.0 / COUNT(*)", "number"),
            ("pct_mujer_ult", "SUM(Mujer_ult) * 100.0 / COUNT(*)", "number"),
            ("pct_con_mujeres", "SUM(Hay_mujeres) * 100.0 / COUNT(*)", "number"),
        ]
        for mname, mexpr, mtype in metrics:
            sm = SqlMetric(
                metric_name=mname,
                expression=mexpr,
                metric_type=mtype,
                table_id=ds.id,
            )
            db.session.add(sm)

        db.session.commit()
        print(f"[country_ds] Created ds_fact_paper_by_country id={ds.id}")


if __name__ == "__main__":
    main()

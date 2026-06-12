"""Idempotent: create 6 dashboards + 25+ charts for the Memoria BI.

Each chart has:
  - viz_type: pie / big_number / bar / line / pivot_table / etc.
  - datasource: dataset name (must exist in Superset)
  - params: the viz config (groupby, metrics, etc.)
  - form_data: same as params (used in chart query)

Charts reference the dataset by ID. We use the SqlaTable ORM.

Run via:
    docker compose run --rm superset python3 /app/cfg/init_dashboards.py
"""
import os

os.environ.setdefault("SUPERSET_CONFIG_PATH", "/app/pythonpath/superset_config.py")


DASHBOARDS = [
    {
        "slug": "resumen-general",
        "title": "01 - Resumen General",
        "description": "KPIs principales y distribucion global",
        "charts": [
            {
                "name": "Total de papers",
                "viz_type": "big_number_total",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "count",
                    "show_trend_line": False,
                    "y_axis_format": ",d",
                },
            },
            {
                "name": "% Mujer Primera Autora",
                "viz_type": "big_number_total",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "pct_mujer_primera",
                    "y_axis_format": ".2f",
                    "header_font_size": 0.3,
                },
            },
            {
                "name": "% Mujer Ultima Autora (PI)",
                "viz_type": "big_number_total",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "pct_mujer_ult",
                    "y_axis_format": ".2f",
                },
            },
            {
                "name": "Papers por Area (treemap)",
                "viz_type": "treemap",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "count",
                    "groupby": ["IdArea"],
                    "custom_label": "papers",
                },
            },
        ],
    },
    {
        "slug": "brecha-por-area",
        "title": "02 - Brecha por Area",
        "description": "Comparacion de la brecha entre areas cientificas",
        "charts": [
            {
                "name": "% Mujer Primera vs Ultima por Area",
                "viz_type": "dist_bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metrics": ["pct_mujer_primera", "pct_mujer_ult"],
                    "groupby": "IdArea",
                    "show_legend": True,
                    "y_axis_format": ".1f",
                },
            },
            {
                "name": "Papers totales por Area",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "count",
                    "groupby": "IdArea",
                    "y_axis_format": ",d",
                },
            },
            {
                "name": "% Con Mujeres por Area",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "pct_con_mujeres",
                    "groupby": "IdArea",
                    "y_axis_format": ".1f",
                },
            },
            {
                "name": "Brecha Primera - Ultima por Area",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "pct_mujer_primera",
                    "groupby": "IdArea",
                    "y_axis_format": ".1f",
                },
            },
        ],
    },
    {
        "slug": "tendencia-temporal",
        "title": "03 - Tendencia Temporal",
        "description": "Evolucion de la brecha a lo largo del tiempo",
        "charts": [
            {
                "name": "% Mujer Primera vs Ultima por Anio",
                "viz_type": "line",
                "dataset": "Fact_Paper",
                "params": {
                    "metrics": ["pct_mujer_primera", "pct_mujer_ult"],
                    "groupby": "IdTiempo",
                    "show_legend": True,
                    "y_axis_format": ".1f",
                },
            },
            {
                "name": "Papers por Anio",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "count",
                    "groupby": "IdTiempo",
                    "y_axis_format": ",d",
                },
            },
            {
                "name": "Promedio Autores por Anio",
                "viz_type": "line",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "avg_n_autores",
                    "groupby": "IdTiempo",
                    "y_axis_format": ".2f",
                },
            },
            {
                "name": "% Unipersonal por Anio",
                "viz_type": "line",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "pct_unipersonal",
                    "groupby": "IdTiempo",
                    "y_axis_format": ".1f",
                },
            },
        ],
    },
    {
        "slug": "brecha-geografica",
        "title": "04 - Brecha Geografica",
        "description": "Distribucion por paises y regiones",
        "charts": [
            {
                "name": "% Mujer Ultima por Region",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "pct_mujer_ult",
                    "groupby": "IdGeo",
                    "y_axis_format": ".1f",
                },
            },
            {
                "name": "Top 20 Paises por Papers",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "count",
                    "groupby": "IdGeo",
                    "row_limit": 20,
                    "y_axis_format": ",d",
                },
            },
            {
                "name": "% Mujer Primera por Region",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "pct_mujer_primera",
                    "groupby": "IdGeo",
                    "y_axis_format": ".1f",
                },
            },
            {
                "name": "Papers por Region (pivot)",
                "viz_type": "pivot_table",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "count",
                    "groupby": ["IdGeo"],
                    "y_axis_format": ",d",
                },
            },
        ],
    },
    {
        "slug": "productividad",
        "title": "05 - Productividad y Autoria",
        "description": "Distribucion de autoria y colaboracion",
        "charts": [
            {
                "name": "Distribucion N Autores",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "count",
                    "groupby": "N_autores",
                    "y_axis_format": ",d",
                },
            },
            {
                "name": "Distribucion N Mujeres",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "count",
                    "groupby": "N_mujeres",
                    "y_axis_format": ",d",
                },
            },
            {
                "name": "% Unipersonal vs Colaborativa",
                "viz_type": "pie",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "count",
                    "groupby": ["N_autores"],
                },
            },
            {
                "name": "% Mujer Primera: Unipersonal vs Colaborativa",
                "viz_type": "pie",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "pct_mujer_primera",
                    "groupby": ["N_autores"],
                },
            },
        ],
    },
    {
        "slug": "calidad-sjr",
        "title": "06 - Calidad (SJR)",
        "description": "Relacion entre factor de impacto y brecha de genero",
        "charts": [
            {
                "name": "Top 20 Journals por Papers",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "count",
                    "groupby": "IdJournal",
                    "row_limit": 20,
                    "y_axis_format": ",d",
                },
            },
            {
                "name": "% Mujer Ultima por Top 20 Journals",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "pct_mujer_ult",
                    "groupby": "IdJournal",
                    "row_limit": 20,
                    "y_axis_format": ".1f",
                },
            },
            {
                "name": "Papers por Anio con SJR (pivot)",
                "viz_type": "pivot_table_v2",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": "count",
                    "groupby": ["IdJournal", "IdTiempo"],
                    "row_limit": 50,
                },
            },
        ],
    },
]


def main():
    from superset.app import create_app
    app = create_app()
    with app.app_context():
        from superset.connectors.sqla.models import SqlaTable
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard
        from superset import db
        from flask_appbuilder.security.sqla.models import User, Role

        datasets_by_name = {ds.table_name: ds for ds in db.session.query(SqlaTable).all()}
        if len(datasets_by_name) != 6:
            print(f"[dashboards] WARNING: expected 6 datasets, found {len(datasets_by_name)}")

        admin = db.session.query(User).filter_by(username="admin").one()
        public_role = db.session.query(Role).filter_by(name="Public").one()

        for dash_def in DASHBOARDS:
            existing = (
                db.session.query(Dashboard).filter_by(slug=dash_def["slug"]).first()
            )
            if existing:
                print(f"[dashboards] {dash_def['slug']} already exists, skipping")
                continue

            dash = Dashboard(
                slug=dash_def["slug"],
                dashboard_title=dash_def["title"],
                description=dash_def["description"],
                owners=[admin],
                created_by=admin,
                changed_by=admin,
            )
            dash.roles = [public_role]
            dash.css = ""
            dash.json_metadata = '{"CHART-KEY":"val"}'
            db.session.add(dash)
            db.session.flush()

            for i, chart_def in enumerate(dash_def["charts"]):
                ds = datasets_by_name.get(chart_def["dataset"])
                if not ds:
                    print(f"  [WARN] dataset {chart_def['dataset']} not found, skipping {chart_def['name']}")
                    continue

                import json
                slice_obj = Slice(
                    slice_name=chart_def["name"],
                    viz_type=chart_def["viz_type"],
                    datasource_id=ds.id,
                    datasource_type="table",
                    datasource_name=f"{ds.schema}.{ds.table_name}",
                    params=json.dumps(chart_def["params"]),
                    description=chart_def["name"],
                    owners=[admin],
                    created_by=admin,
                    changed_by=admin,
                    dashboards=[dash],
                )
                db.session.add(slice_obj)
                db.session.flush()
                print(f"  created chart id={slice_obj.id} {chart_def['name']}")

            dash.position_json = "{}"
            db.session.commit()
            print(f"[dashboards] Created {dash_def['slug']} id={dash.id} charts={len(dash_def['charts'])}")

        print(f"[dashboards] Done. Total dashboards: {db.session.query(Dashboard).count()}")


if __name__ == "__main__":
    main()

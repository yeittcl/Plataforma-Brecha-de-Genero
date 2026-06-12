"""Idempotent: create 6 dashboards + 24 charts for the Memoria BI.

Each chart has:
  - viz_type: pie / big_number / bar / line / pivot_table / etc.
  - datasource: dataset name (must exist in Superset)
  - params: the viz config in Superset format
    - metric (single): {"label": "count"} references dataset's virtual metric
    - metrics (list): [{"label": "count"}, {"label": "pct_mujer_ult"}]
    - Or SQL: {"label": "X", "expressionType": "SQL", "sqlExpression": "..."}
  - groupby: column name (string) or list of column names

Charts reference the dataset by ID. We use the SqlaTable ORM.

Run via:
    docker compose run --rm superset python3 /app/cfg/init_dashboards.py
"""
import os

os.environ.setdefault("SUPERSET_CONFIG_PATH", "/app/pythonpath/superset_config.py")


def M(label):
    """Make a metric dict referencing a dataset virtual metric by label."""
    return {"label": label}


def SQL(label, expr):
    """Make an inline SQL metric."""
    return {"label": label, "expressionType": "SQL", "sqlExpression": expr}


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
                    "metric": M("count"),
                    "y_axis_format": ",d",
                },
            },
            {
                "name": "% Mujer Primera Autora",
                "viz_type": "big_number_total",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": M("pct_mujer_primera"),
                    "y_axis_format": ".2f",
                },
            },
            {
                "name": "% Mujer Ultima Autora (PI)",
                "viz_type": "big_number_total",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": M("pct_mujer_ult"),
                    "y_axis_format": ".2f",
                },
            },
            {
                "name": "Papers por Area (treemap)",
                "viz_type": "treemap",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": M("count"),
                    "groupby": ["IdArea"],
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
                    "metrics": [M("pct_mujer_primera"), M("pct_mujer_ult")],
                    "groupby": ["IdArea"],
                    "show_legend": True,
                    "y_axis_format": ".1f",
                    "groupby_type": "dimension",
                    "show_total": False,
                },
            },
            {
                "name": "Papers totales por Area",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metrics": [M("count")],
                    "groupby": ["IdArea"],
                    "y_axis_format": ",d",
                    "row_limit": 30,
                },
            },
            {
                "name": "% Con Mujeres por Area",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metrics": [M("pct_con_mujeres")],
                    "groupby": ["IdArea"],
                    "y_axis_format": ".1f",
                    "row_limit": 30,
                },
            },
            {
                "name": "% Unipersonal por Area",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metrics": [M("pct_unipersonal")],
                    "groupby": ["IdArea"],
                    "y_axis_format": ".1f",
                    "row_limit": 30,
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
                    "metrics": [M("pct_mujer_primera"), M("pct_mujer_ult")],
                    "groupby": ["IdTiempo"],
                    "show_legend": True,
                    "y_axis_format": ".1f",
                    "x_axis": "IdTiempo",
                    "line_interpolation": "linear",
                },
            },
            {
                "name": "Papers por Anio",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metrics": [M("count")],
                    "groupby": ["IdTiempo"],
                    "y_axis_format": ",d",
                },
            },
            {
                "name": "Promedio Autores por Anio",
                "viz_type": "line",
                "dataset": "Fact_Paper",
                "params": {
                    "metrics": [M("avg_n_autores")],
                    "groupby": ["IdTiempo"],
                    "y_axis_format": ".2f",
                    "x_axis": "IdTiempo",
                },
            },
            {
                "name": "% Unipersonal por Anio",
                "viz_type": "line",
                "dataset": "Fact_Paper",
                "params": {
                    "metrics": [M("pct_unipersonal")],
                    "groupby": ["IdTiempo"],
                    "y_axis_format": ".1f",
                    "x_axis": "IdTiempo",
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
                    "metrics": [M("pct_mujer_ult")],
                    "groupby": ["IdGeo"],
                    "y_axis_format": ".1f",
                    "row_limit": 30,
                },
            },
            {
                "name": "Top 20 Paises por Papers",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metrics": [M("count")],
                    "groupby": ["IdGeo"],
                    "row_limit": 20,
                    "y_axis_format": ",d",
                },
            },
            {
                "name": "% Mujer Primera por Region",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metrics": [M("pct_mujer_primera")],
                    "groupby": ["IdGeo"],
                    "y_axis_format": ".1f",
                    "row_limit": 30,
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
                    "metrics": [M("count")],
                    "groupby": ["N_autores"],
                    "y_axis_format": ",d",
                },
            },
            {
                "name": "Distribucion N Mujeres",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metrics": [M("count")],
                    "groupby": ["N_mujeres"],
                    "y_axis_format": ",d",
                },
            },
            {
                "name": "% Mujer Primera vs N Autores",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metrics": [M("pct_mujer_primera")],
                    "groupby": ["N_autores"],
                    "y_axis_format": ".1f",
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
                    "metrics": [M("count")],
                    "groupby": ["IdJournal"],
                    "row_limit": 20,
                    "y_axis_format": ",d",
                },
            },
            {
                "name": "% Mujer Ultima por Top 20 Journals",
                "viz_type": "bar",
                "dataset": "Fact_Paper",
                "params": {
                    "metrics": [M("pct_mujer_ult")],
                    "groupby": ["IdJournal"],
                    "row_limit": 20,
                    "y_axis_format": ".1f",
                },
            },
        ],
    },
    {
        "slug": "mapa-geografico",
        "title": "07 - Mapa Geografico",
        "description": "Distribucion de papers por pais en el mundo",
        "charts": [
            {
                "name": "Papers por Pais (mapa mundial)",
                "viz_type": "world_map",
                "dataset": "Fact_Paper",
                "params": {
                    "metric": M("count"),
                    "entity": "country_name",
                    "country_fieldtype": "cca2",
                    "groupby": ["NombrePais"],
                    "viz_type": "world_map",
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
        if len(datasets_by_name) < 6:
            print(f"[dashboards] WARNING: expected 6+ datasets, found {len(datasets_by_name)}")

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
            dash.json_metadata = "{}"
            db.session.add(dash)
            db.session.flush()

            import json
            for chart_def in dash_def["charts"]:
                ds = datasets_by_name.get(chart_def["dataset"])
                if not ds:
                    print(f"  [WARN] dataset {chart_def['dataset']} not found, skipping {chart_def['name']}")
                    continue

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

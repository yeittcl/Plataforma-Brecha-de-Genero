"""Export dashboards + their charts as separate YAML files in superset/dashboards/."""
import os
from pathlib import Path
import yaml

os.environ.setdefault("SUPERSET_CONFIG_PATH", "/app/pythonpath/superset_config.py")

from superset.app import create_app
app = create_app()
with app.app_context():
    from superset import db
    from superset.models.dashboard import Dashboard
    from superset.models.slice import Slice

    out_dir = Path("/app/out/dashboards")
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("*.yaml"):
        f.unlink()

    for dash in db.session.query(Dashboard).order_by(Dashboard.id).all():
        dash_payload = {
            "dashboard_title": dash.dashboard_title,
            "slug": dash.slug,
            "description": dash.description,
            "css": dash.css or "",
            "position_json": dash.position_json or "{}",
            "json_metadata": dash.json_metadata or "{}",
            "published": bool(dash.published),
            "version": "1.0.0",
            "charts": [],
        }
        for slc in dash.slices:
            chart_payload = {
                "slice_name": slc.slice_name,
                "viz_type": slc.viz_type,
                "datasource_id": slc.datasource_id,
                "datasource_type": slc.datasource_type,
                "datasource_name": slc.datasource_name,
                "params": slc.params,
                "description": slc.description,
            }
            dash_payload["charts"].append(chart_payload)
        yaml_path = out_dir / f"{dash.slug}.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(dash_payload, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        print(f"[export] Wrote {yaml_path} charts={len(dash.slices)}")

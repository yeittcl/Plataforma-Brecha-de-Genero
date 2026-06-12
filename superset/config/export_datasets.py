"""Export all Superset datasets (datasources) to YAML files in a directory."""
import importlib.util
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

os.environ.setdefault("SUPERSET_CONFIG_PATH", "/app/pythonpath/superset_config.py")


def main():
    from superset.app import create_app

    app = create_app()
    with app.app_context():
        from superset.extensions import db
        from superset.connectors.sqla.models import SqlaTable

        datasets = db.session.query(SqlaTable).all()
        print(f"[export] Found {len(datasets)} datasets")

        out_dir = Path("/tmp/datasets_export")
        out_dir.mkdir(exist_ok=True)
        for f in out_dir.glob("*.yaml"):
            f.unlink()
        for f in out_dir.glob("*.yml"):
            f.unlink()

        for ds in datasets:
            ds_payload = ds.export_to_dict(
                recursive=True,
                include_parent_ref=False,
                include_defaults=True,
            )
            ds_payload["version"] = "1.0.0"
            ds_payload["database_uuid"] = str(ds.database.uuid) if ds.database else None

            yaml_path = out_dir / f"{ds.table_name}.yaml"
            import yaml
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(ds_payload, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
            print(f"[export] Wrote {yaml_path}")

        out_zip = Path("/tmp/datasets_export.zip")
        if out_zip.exists():
            out_zip.unlink()
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in out_dir.glob("*.yaml"):
                zf.write(p, p.name)
        print(f"[export] Wrote {out_zip} ({out_zip.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

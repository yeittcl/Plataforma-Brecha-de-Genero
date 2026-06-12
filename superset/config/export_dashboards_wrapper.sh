#!/bin/bash
set -e
python3 -c "
import os
os.environ.setdefault('SUPERSET_CONFIG_PATH', '/app/pythonpath/superset_config.py')
import importlib.util
spec = importlib.util.spec_from_file_location('m', '/app/cfg/export_dashboards.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
"
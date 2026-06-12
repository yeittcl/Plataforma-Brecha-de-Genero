#!/bin/bash
set -e

echo "[init] Waiting for Superset webserver..."
for i in {1..60}; do
    if curl -sf http://superset:8088/health > /dev/null 2>&1; then
        echo "[init] Superset is healthy"
        break
    fi
    sleep 5
    if [ "$i" -eq 60 ]; then
        echo "[init] ERROR: Superset did not become healthy"
        exit 1
    fi
done

echo "[init] Running superset db upgrade..."
superset db upgrade

echo "[init] Running superset init..."
superset init

echo "[init] Creating admin user ${SUPERSET_ADMIN_USERNAME}..."
superset fab create-admin \
    --username "${SUPERSET_ADMIN_USERNAME}" \
    --firstname "Admin" \
    --lastname "Memoria" \
    --email "${SUPERSET_ADMIN_EMAIL}" \
    --password "${SUPERSET_ADMIN_PASSWORD}" \
    || echo "[init] Admin user already exists"

echo "[init] Public role mirrors Gamma via PUBLIC_ROLE_LIKE config (no action needed)"

echo "[init] Importing database connection for ClickHouse..."
python3 -c "import importlib.util; spec = importlib.util.spec_from_file_location('init_db', '/app/cfg/init_db.py'); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); mod.main()"

echo "[init] Done."

FROM apache/superset:3.1.3

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-local.txt /app/requirements-local.txt
RUN pip install --no-cache-dir -r /app/requirements-local.txt

ENV SUPERSET_CONFIG_PATH=/app/pythonpath/superset_config.py

USER superset

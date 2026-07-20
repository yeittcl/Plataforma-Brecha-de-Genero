import os

from flask_caching import Cache

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "change-me-in-production")

SQLALCHEMY_DATABASE_URI = "sqlite:////app/superset_home/superset.db"

ROW_LIMIT = 50000
SUPERSET_WEBSERVER_PORT = 8088

PUBLIC_ROLE_LIKE = "Gamma"
ENABLE_PROXY_FIX = True
AUTH_USER_REGISTRATION = False
AUTH_USER_REGISTRATION_ROLE = "Public"

FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "DASHBOARD_RBAC": False,
    "EMBEDDED_SUPERSET": True,
    "ALERT_REPORTS": False,
}

WTF_CSRF_ENABLED = True
WTF_CSRF_EXEMPT_LIST = ["superset.views.core.log", "superset.charts.data.api.data"]

LANGUAGES = {
    "en": {"flag": "us", "name": "English"},
    "es": {"flag": "es", "name": "Español"},
}

# --- Celery + Redis (for SQL Lab async queries and caching) ---
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

# Top-level config (consumed by superset.tasks.celery_app)
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", f"redis://{REDIS_HOST}:{REDIS_PORT}/1")

CELERY_CONFIG = {
    "broker_url": CELERY_BROKER_URL,
    "results_backend": CELERY_RESULT_BACKEND,
    "worker_prefetch_multiplier": 1,
    "task_acks_late": False,
}

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": 2,
}

DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": 3,
    "CACHE_DEFAULT_TIMEOUT": 300,
}

# SQL Lab is fundamentally broken with clickhouse-sqlalchemy 0.2.7 + Superset 3.1.3.
# The result processing always fails because of `'str' object has no attribute 'set'`
# or the Cache object being put as the error message. We disable SQL Lab by
# setting the database flag `allow_run_async = False` (set via ORM after init).
# For the thesis demo, the workflow is: create virtual datasets via the ORM
# script `init_country_ds.py` (and similar), then consume them in charts.

# Celery + Redis are still configured for the worker to be available
# (useful for future use), but the database doesn't allow async queries.
RESULTS_BACKEND = None
RESULTS_BACKEND_USE_MSGPACK = False
SQLLAB_TIMEOUT = 300
SQLLAB_CTAS_NO_LIMIT = True
SQLLAB_ASYNC_TIME_LIMIT_SEC = 0
PREFETCH_XLIB_TABLES = False
SQLLAB_ALLOW_SQLLAB_ASYNC_FALSE = True

LOGO_TARGET_PATH = "#"



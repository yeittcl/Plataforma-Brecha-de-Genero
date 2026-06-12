import os

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "change-me-in-production")

SQLALCHEMY_DATABASE_URI = "sqlite:////app/superset_home/superset.db"

ROW_LIMIT = 50000
SUPERSET_WEBSERVER_PORT = 8088

PUBLIC_ROLE_LIKE = "Gamma"
AUTH_USER_REGISTRATION = False
AUTH_USER_REGISTRATION_ROLE = "Public"

FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "DASHBOARD_RBAC": True,
    "EMBEDDED_SUPERSET": True,
    "ALERT_REPORTS": False,
}

WTF_CSRF_ENABLED = True
WTF_CSRF_EXEMPT_LIST = ["superset.views.core.log", "superset.charts.data.api.data"]

LANGUAGES = {
    "en": {"flag": "us", "name": "English"},
    "es": {"flag": "es", "name": "Español"},
}

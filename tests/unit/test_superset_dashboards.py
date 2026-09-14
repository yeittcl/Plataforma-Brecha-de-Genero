"""Unit tests for SQL helper and METRICS/DASHBOARDS in superset/config/init_dashboards.py."""
import importlib.util
import os

spec = importlib.util.spec_from_file_location(
    "init_dashboards",
    os.path.join(os.path.dirname(__file__), "..", "..", "superset", "config", "init_dashboards.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestSQLHelper:
    def test_returns_dict(self):
        result = mod.SQL("label", "expr")
        assert isinstance(result, dict)

    def test_has_expected_keys(self):
        result = mod.SQL("test", "test_expr")
        assert result == {
            "label": "test",
            "expressionType": "SQL",
            "sqlExpression": "test_expr",
        }

    def test_metrics_count(self):
        assert len(mod.METRICS) == 14

    def test_dashboards_count(self):
        assert len(mod.DASHBOARDS) == 7

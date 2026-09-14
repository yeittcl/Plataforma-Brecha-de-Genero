"""E2E tests: validate ETL script structure and importability."""
import importlib.util
import os
import sys


class TestETLImports:
    """Verify all ETL modules can be imported (syntax check)."""

    def _load_module(self, name, rel_path):
        path = os.path.join(os.path.dirname(__file__), "..", "..", rel_path)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            return mod
        except SystemExit:
            return mod

    def test_import_common(self):
        mod = self._load_module("common", os.path.join("etl", "common.py"))
        assert hasattr(mod, "normalize_position")
        assert hasattr(mod, "normalize_country")
        assert hasattr(mod, "truncate")

    def test_import_load_clickhouse(self):
        mod = self._load_module("load_clickhouse", os.path.join("etl", "load_clickhouse.py"))
        assert hasattr(mod, "_quote_col")
        assert hasattr(mod, "_insert_batch")

    def test_import_load_postgres(self):
        mod = self._load_module("load_postgres", os.path.join("etl", "load_postgres.py"))
        assert callable(mod.main)

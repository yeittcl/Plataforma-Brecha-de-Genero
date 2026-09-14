"""Unit tests for DATASETS structure in superset/config/init_datasets.py."""
import importlib.util
import os

spec = importlib.util.spec_from_file_location(
    "init_datasets", os.path.join(os.path.dirname(__file__), "..", "..", "superset", "config", "init_datasets.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestDatasets:
    def test_count(self):
        assert len(mod.DATASETS) == 6

    def test_has_table_names(self):
        for ds in mod.DATASETS:
            assert "table_name" in ds
            assert isinstance(ds["table_name"], str)

    def test_has_schema(self):
        for ds in mod.DATASETS:
            assert ds["schema"] == "memoria"

    def test_fact_paper_has_metrics(self):
        fact = next(ds for ds in mod.DATASETS if ds["table_name"] == "Fact_Paper")
        assert "metrics" in fact
        assert len(fact["metrics"]) == 14

    def test_fact_paper_columns(self):
        fact = next(ds for ds in mod.DATASETS if ds["table_name"] == "Fact_Paper")
        col_names = [c[0] for c in fact["columns"]]
        assert "Mujer_primera" in col_names
        assert "N_autores" in col_names

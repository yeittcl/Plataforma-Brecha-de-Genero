"""Unit tests for _quote_col in load_clickhouse."""
from etl.load_clickhouse import _quote_col


class TestQuoteCol:
    def test_ascii(self):
        assert _quote_col("Area") == "Area"

    def test_non_ascii(self):
        assert _quote_col("Año") == '"Año"'

    def test_special_chars(self):
        assert _quote_col("Column with spaces") == "Column with spaces"

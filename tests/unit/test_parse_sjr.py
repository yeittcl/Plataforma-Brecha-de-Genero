"""Unit tests for parse_sjr_value and find_journal_id in load_postgres_sjr."""
from etl.load_postgres_sjr import parse_sjr_value, find_journal_id


class TestParseSjrValue:
    def test_nan(self):
        import math
        result = parse_sjr_value(float("nan"))
        assert result is None or math.isnan(result)

    def test_comma_decimal(self):
        result = parse_sjr_value("1,23")
        assert result == 1.23

    def test_normal(self):
        result = parse_sjr_value("2.5")
        assert result == 2.5

    def test_empty(self):
        result = parse_sjr_value("")
        assert result is None


class TestFindJournalId:
    def test_found(self):
        journals = {"NATURE": 5, "SCIENCE": 10}
        assert find_journal_id("Nature", journals) == 5

    def test_not_found(self):
        journals = {"NATURE": 5}
        assert find_journal_id("X", journals) is None

    def test_empty_title(self):
        journals = {"NATURE": 5}
        assert find_journal_id("", journals) is None

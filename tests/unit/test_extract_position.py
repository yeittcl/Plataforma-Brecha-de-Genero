"""Unit tests for _extract_position_from_id in sources/autor."""
from etl.sources.autor import _extract_position_from_id


class TestExtractPosition:
    def test_valid(self):
        assert _extract_position_from_id("abc-123-2") == "2"

    def test_no_dash(self):
        assert _extract_position_from_id("abc") == "0"

    def test_empty(self):
        assert _extract_position_from_id("") == "0"

    def test_multiple_dashes(self):
        assert _extract_position_from_id("a-b-c-5") == "5"

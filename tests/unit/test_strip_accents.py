"""Unit tests for strip_accents in load_postgres_publishers."""
from etl.load_postgres_publishers import strip_accents


class TestStripAccents:
    def test_cafe(self):
        assert strip_accents("café") == "cafe"

    def test_no_accents(self):
        assert strip_accents("hello") == "hello"

    def test_spanish(self):
        assert strip_accents("José") == "Jose"

    def test_empty(self):
        assert strip_accents("") == ""

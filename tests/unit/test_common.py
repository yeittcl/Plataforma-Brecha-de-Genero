"""Unit tests for etl/common.py — pure functions."""
from etl.common import normalize_position, normalize_country, normalize_firstname, truncate


class TestNormalizePosition:
    def test_first(self):
        assert normalize_position("first") == "first"

    def test_fist_typo(self):
        assert normalize_position("fist") == "first"

    def test_last(self):
        assert normalize_position("last") == "last"

    def test_penultimate(self):
        assert normalize_position("penultimate") == "penultimate"

    def test_second(self):
        assert normalize_position("second") == "second"

    def test_empty(self):
        assert normalize_position("") == "other"

    def test_unknown(self):
        assert normalize_position("random") == "other"

    def test_whitespace(self):
        assert normalize_position("  first  ") == "first"

    def test_case_insensitive(self):
        assert normalize_position("FIRST") == "first"


class TestNormalizeCountry:
    def test_uk(self):
        assert normalize_country("UK") == "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND"

    def test_usa(self):
        assert normalize_country("USA") == "UNITED STATES"

    def test_russia(self):
        assert normalize_country("Russia") == "RUSSIAN FEDERATION"

    def test_empty(self):
        assert normalize_country("") == "Unknown"

    def test_whitespace(self):
        assert normalize_country("  China  ") == "CHINA"

    def test_britain(self):
        assert normalize_country("Britain") == "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND"

    def test_korea_south(self):
        assert normalize_country("South Korea") == "KOREA SOUTH"


class TestNormalizeFirstname:
    def test_normal(self):
        assert normalize_firstname("  maria  ") == "Maria"

    def test_empty(self):
        assert normalize_firstname("") == "Unknown"

    def test_title_case(self):
        assert normalize_firstname("JOHN") == "John"


class TestTruncate:
    def test_short(self):
        assert truncate("hi", 10) == "hi"

    def test_long(self):
        assert truncate("hello", 3) == "hel"

    def test_exact(self):
        assert truncate("hello", 5) == "hello"

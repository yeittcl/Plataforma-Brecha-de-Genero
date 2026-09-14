"""Integration tests: validate schema DDL and ETL config consistency."""
import os
import re


def _read_sql_file(filename):
    path = os.path.join(os.path.dirname(__file__), "..", "..", "db", filename)
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestClickHouseSchema:
    def setup_method(self):
        self.ddl = _read_sql_file("clickhouse_schema.sql")

    def test_has_fact_paper(self):
        assert "Fact_Paper" in self.ddl

    def test_has_all_dims(self):
        for dim in ["Dim_Area", "Dim_Geografica", "Dim_Journal", "Dim_Tiempo", "Dim_FactorImpacto"]:
            assert dim in self.ddl

    def test_merge_tree_engine(self):
        engines = re.findall(r"ENGINE\s*=\s*\w+", self.ddl)
        assert len(engines) >= 6

    def test_order_by_present(self):
        order_bys = re.findall(r"ORDER BY\s*\(", self.ddl)
        assert len(order_bys) >= 2

    def test_partition_by(self):
        assert "PARTITION BY" in self.ddl


class TestPostgresSchema:
    def setup_method(self):
        self.ddl = _read_sql_file("01_schema.sql")

    def test_has_core_tables(self):
        for table in ["Paper", "Investigador", "Journal", "Area", "Pais", "Posicion"]:
            assert f'"{table}"' in self.ddl

    def test_has_constraints(self):
        assert "PRIMARY KEY" in self.ddl or "PRIMARY" in self.ddl

    def test_has_foreign_keys(self):
        assert "FOREIGN KEY" in self.ddl

    def test_has_enums(self):
        assert "genero_enum" in self.ddl
        assert "posicion_enum" in self.ddl

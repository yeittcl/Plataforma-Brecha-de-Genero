import argparse
import logging
import time
from typing import Optional

from etl.common import get_clickhouse_cnx, get_postgres_cnx, load_env

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BATCH_SIZE = 10_000


def _truncate(ch, table: str) -> None:
    ch.command(f"TRUNCATE TABLE IF EXISTS {table}")


def _quote_col(name: str) -> str:
    if any(ord(c) > 127 for c in name):
        return f'"{name}"'
    return name


def _insert_batch(ch, table: str, columns: list[str], rows: list[tuple]) -> None:
    if not rows:
        return
    quoted_cols = [_quote_col(c) for c in columns]
    placeholders = ",".join(["(" + ",".join(["%s"] * len(columns)) + ")"] * len(rows))
    flat_values = [v for row in rows for v in row]
    ch.command(
        f"INSERT INTO {table} ({','.join(quoted_cols)}) VALUES {placeholders}",
        parameters=flat_values,
    )


def load_dim_geografica(pg, ch) -> int:
    log.info("Loading Dim_Geografica...")
    with pg.cursor() as cur:
        cur.execute("""
            SELECT p."Id", p."Nombre", COALESCE(r."Nombre", 'Unknown') AS Region
            FROM "Pais" p
            LEFT JOIN "Region" r ON r."Id" = p."Id_Region"
            ORDER BY p."Id"
        """)
        rows = cur.fetchall()
    _truncate(ch, "Dim_Geografica")
    _insert_batch(ch, "Dim_Geografica", ["IdGeo", "NombrePais", "NombreRegion"],
                  [(r[0], r[1], r[2]) for r in rows])
    log.info(f"  Dim_Geografica: {len(rows)} rows")
    return len(rows)


def load_dim_tiempo(pg, ch) -> int:
    log.info("Loading Dim_Tiempo...")
    with pg.cursor() as cur:
        cur.execute("SELECT DISTINCT \"Año\" FROM \"Paper\" WHERE \"Año\" IS NOT NULL ORDER BY \"Año\"")
        years = [r[0] for r in cur.fetchall()]
    if not years:
        years = list(range(1999, 2026))
    _truncate(ch, "Dim_Tiempo")
    rows = []
    for year in years:
        decada = f"{(year // 10) * 10}s"
        siglo = "XXI" if year > 2000 else "XX"
        rows.append((year, year, decada, siglo, None))
    _insert_batch(ch, "Dim_Tiempo", ["IdTiempo", "Año", "Decada", "Siglo", "Hito"], rows)
    log.info(f"  Dim_Tiempo: {len(rows)} rows")
    return len(rows)


def load_dim_area(pg, ch) -> int:
    log.info("Loading Dim_Area...")
    with pg.cursor() as cur:
        cur.execute("""
            SELECT ac."IdArea", a."Nombre", c."Nombre"
            FROM "Area_Categoria" ac
            JOIN "Area" a ON a."Id" = ac."IdArea"
            JOIN "Categoria" c ON c."Id" = ac."IdCategoria"
            ORDER BY ac."IdArea"
        """)
        rows = cur.fetchall()
    _truncate(ch, "Dim_Area")
    _insert_batch(ch, "Dim_Area", ["IdArea", "NombreArea", "NombreCategoria"],
                  [(r[0], r[1], r[2]) for r in rows])
    log.info(f"  Dim_Area: {len(rows)} rows")
    return len(rows)


def load_dim_journal(pg, ch) -> int:
    log.info("Loading Dim_Journal...")
    with pg.cursor() as cur:
        cur.execute("""
            SELECT j."Id", j."Nombre", e."Nombre"
            FROM "Journal" j
            LEFT JOIN "Editorial" e ON e."Id" = j."Id_Editorial"
            ORDER BY j."Id"
        """)
        rows = cur.fetchall()
    _truncate(ch, "Dim_Journal")
    _insert_batch(ch, "Dim_Journal", ["IdJournal", "NombreJournal", "NombreEditorial"],
                  [(r[0], r[1], r[2]) for r in rows])
    log.info(f"  Dim_Journal: {len(rows)} rows")
    return len(rows)


def load_dim_factor_impacto(pg, ch) -> int:
    log.info("Loading Dim_FactorImpacto...")
    with pg.cursor() as cur:
        cur.execute("""
            SELECT j."Id", f."Año", f."Valor"
            FROM "Factor_Impacto" f
            JOIN "Journal" j ON j."Id" = f."Id_Journal"
            WHERE f."Año" IS NOT NULL
            ORDER BY j."Id", f."Año"
        """)
        rows = cur.fetchall()
    _truncate(ch, "Dim_FactorImpacto")
    fact_rows = []
    next_id = 1
    for jid, year, valor in rows:
        fact_rows.append((next_id, jid, year, float(valor)))
        next_id += 1
    _insert_batch(ch, "Dim_FactorImpacto",
                  ["IdFactorImpacto", "IdJournal", "Año", "SJR"], fact_rows)
    log.info(f"  Dim_FactorImpacto: {len(fact_rows)} rows")
    return len(fact_rows)


def fetch_fact_batch(pg, journal_lookup: dict, area_lookup: dict,
                     geo_lookup: dict, tiempo_lookup: dict, offset: int, limit: int) -> list:
    with pg.cursor() as cur:
        cur.execute("""
            WITH contrib AS (
                SELECT
                    c."IdPaper",
                    c."IdInvestigador",
                    c."PosicionOrdinal",
                    i."Genero",
                    COUNT(*) OVER (PARTITION BY c."IdPaper") AS total_contrib,
                    ROW_NUMBER() OVER (PARTITION BY c."IdPaper" ORDER BY c."PosicionOrdinal") AS rn_asc,
                    ROW_NUMBER() OVER (PARTITION BY c."IdPaper" ORDER BY c."PosicionOrdinal" DESC) AS rn_desc
                FROM "Contribucion" c
                JOIN "Investigador" i ON i."Id" = c."IdInvestigador"
            ),
            flags AS (
                SELECT
                    "IdPaper",
                    MAX(CASE WHEN rn_asc = 1 AND "Genero" = 'female' THEN 1 ELSE 0 END) AS mujer_primera,
                    MAX(CASE WHEN total_contrib > 1 AND rn_asc = total_contrib - 1 AND "Genero" = 'female' THEN 1 ELSE 0 END) AS mujer_penult,
                    MAX(CASE WHEN rn_desc = 1 AND "Genero" = 'female' THEN 1 ELSE 0 END) AS mujer_ult,
                    MAX(CASE WHEN "Genero" = 'female' THEN 1 ELSE 0 END) AS hay_mujeres,
                    MAX(CASE WHEN total_contrib = 1 AND "Genero" = 'female' THEN 1 ELSE 0 END) AS mujer_autora,
                    COUNT(*) FILTER (WHERE "Genero" = 'female')::int AS n_mujeres,
                    MAX(total_contrib)::int AS n_autores
                FROM contrib
                GROUP BY "IdPaper"
            )
            SELECT
                p."Id", p."Año", p."Id_Pais", p."Id_Journal", p."Id_Categoria",
                f.mujer_primera, f.mujer_penult, f.mujer_ult, f.hay_mujeres, f.mujer_autora,
                f.n_mujeres, f.n_autores
            FROM "Paper" p
            JOIN flags f ON f."IdPaper" = p."Id"
            WHERE p."Año" IS NOT NULL
              AND p."Id_Pais" IS NOT NULL
              AND p."Id_Journal" IS NOT NULL
              AND p."Id_Categoria" IS NOT NULL
            ORDER BY p."Id"
            OFFSET %s LIMIT %s
        """, (offset, limit))
        return cur.fetchall()


def load_fact_paper(pg, ch) -> int:
    log.info("Building lookup dicts from dimensions...")
    t0 = time.time()
    ch_result = ch.query("SELECT IdJournal FROM Dim_Journal").result_rows
    journal_lookup = {jid: jid for (jid,) in ch_result}

    with pg.cursor() as cur:
        cur.execute('SELECT "IdCategoria", "IdArea" FROM "Area_Categoria"')
        area_lookup = dict(cur.fetchall())

    ch_result = ch.query("SELECT IdGeo, IdGeo FROM Dim_Geografica").result_rows
    geo_lookup = {geo: geo for (geo,) in ch_result}

    ch_result = ch.query("SELECT Año, IdTiempo FROM Dim_Tiempo").result_rows
    tiempo_lookup = {int(year): int(tid) for year, tid in ch_result}
    log.info(f"  Lookups built in {time.time() - t0:.1f}s")

    with pg.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM \"Paper\" WHERE \"Año\" IS NOT NULL")
        total_papers = cur.fetchone()[0]
    log.info(f"  Total papers to process: {total_papers}")

    _truncate(ch, "Fact_Paper")

    columns = [
        "IdPaper", "IdTiempo", "IdGeo", "IdJournal", "IdArea",
        "Mujer_primera", "Mujer_penult", "Mujer_ult", "Hay_mujeres", "Mujer_Autora",
        "N_mujeres", "N_autores",
    ]

    inserted = 0
    offset = 0
    while offset < total_papers:
        rows = fetch_fact_batch(pg, journal_lookup, area_lookup, geo_lookup, tiempo_lookup,
                                offset, BATCH_SIZE)
        if not rows:
            break

        ch_rows = []
        for r in rows:
            paper_id, year, pais_id, jid, cat_id, m1, m2, m3, hm, ma, nm, na = r
            id_tiempo = tiempo_lookup.get(int(year))
            id_geo = geo_lookup.get(int(pais_id))
            id_journal = int(jid)
            id_area = area_lookup.get(int(cat_id))
            if id_tiempo is None or id_geo is None or id_area is None:
                continue
            ch_rows.append((
                int(paper_id), int(id_tiempo), int(id_geo), int(id_journal), int(id_area),
                int(m1), int(m2), int(m3), int(hm), int(ma),
                min(int(nm), 255), min(int(na), 255),
            ))

        if ch_rows:
            _insert_batch(ch, "Fact_Paper", columns, ch_rows)
            inserted += len(ch_rows)

        offset += BATCH_SIZE
        if inserted % 50_000 < BATCH_SIZE:
            log.info(f"  Fact_Paper progress: {inserted:,}/{total_papers:,}")

    log.info(f"  Fact_Paper done: {inserted:,} rows in {time.time() - t0:.1f}s")
    return inserted


def main():
    parser = argparse.ArgumentParser(
        description="ETL from Postgres to ClickHouse DW. See DATAWAREHOUSE.md for the schema."
    )
    parser.add_argument(
        "--mode", choices=["all", "dims", "dim", "fact"], default="all",
        help="all=dims+fact, dims=all 5 dimensions, dim=one dimension (requires --dim), fact=only Fact_Paper"
    )
    parser.add_argument(
        "--dim", choices=["geografica", "tiempo", "area", "journal", "factor_impacto"],
        help="Which single dim to load (only with --mode dim)"
    )
    args = parser.parse_args()

    if args.mode == "dim" and not args.dim:
        parser.error("--mode dim requires --dim")
    if args.dim and args.mode not in ("dim",):
        parser.error("--dim only applies to --mode dim")

    load_env()
    pg = get_postgres_cnx()
    ch = get_clickhouse_cnx()
    log.info("Connected to Postgres and ClickHouse")

    dim_funcs = {
        "geografica": load_dim_geografica,
        "tiempo": load_dim_tiempo,
        "area": load_dim_area,
        "journal": load_dim_journal,
        "factor_impacto": load_dim_factor_impacto,
    }

    if args.mode in ("all", "dims"):
        for name, fn in dim_funcs.items():
            fn(pg, ch)

    if args.mode == "dim":
        dim_funcs[args.dim](pg, ch)

    if args.mode in ("all", "fact"):
        load_fact_paper(pg, ch)

    log.info("All done.")


if __name__ == "__main__":
    main()
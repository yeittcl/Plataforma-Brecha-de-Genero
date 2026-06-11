import logging

from etl.common import get_postgres_cnx, load_env

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def top_10_journals_with_most_sjr_years(conn):
    header("Top 10 journals con más años de SJR data")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT j."Nombre", COUNT(*) AS n_years,
                   ROUND(AVG(f."Valor")::numeric, 4) AS avg_sjr,
                   MIN(f."Año") AS first_year,
                   MAX(f."Año") AS last_year
            FROM "Factor_Impacto" f
            JOIN "Journal" j ON j."Id" = f."Id_Journal"
            GROUP BY j."Id", j."Nombre"
            ORDER BY n_years DESC
            LIMIT 10
        """)
        rows = cur.fetchall()
        print(f"{'Journal':<50s} {'Years':>6s} {'Avg SJR':>10s} {'Range':>14s}")
        print("-" * 82)
        for nombre, n_years, avg_sjr, first, last in rows:
            print(f"{nombre[:48]:<50s} {n_years:>6d} {avg_sjr:>10.4f} {first}-{last:>6}")


def example_journal_without_sjr(conn):
    header("Ejemplo: journals SIN Factor_Impacto")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT j."Id", j."Nombre"
            FROM "Journal" j
            LEFT JOIN "Factor_Impacto" f ON f."Id_Journal" = j."Id"
            WHERE f."Id" IS NULL
            ORDER BY j."Nombre"
            LIMIT 5
        """)
        rows = cur.fetchall()
        print(f"Found {len(rows)} sample journals without any SJR data:")
        for jid, nombre in rows:
            print(f"  [{jid:>4d}] {nombre}")


def sjr_coverage_by_year(conn):
    header("Cobertura de SJR por año (número de journals con SJR data)")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT "Año", COUNT(*) AS n_journals,
                   ROUND(AVG("Valor")::numeric, 4) AS avg_sjr,
                   ROUND(MIN("Valor")::numeric, 4) AS min_sjr,
                   ROUND(MAX("Valor")::numeric, 4) AS max_sjr
            FROM "Factor_Impacto"
            GROUP BY "Año"
            ORDER BY "Año" DESC
        """)
        rows = cur.fetchall()
        print(f"{'Year':>6s} {'Journals':>10s} {'Avg SJR':>10s} {'Min':>8s} {'Max':>8s}")
        print("-" * 48)
        for year, n, avg, minv, maxv in rows:
            print(f"{year:>6d} {n:>10d} {avg:>10.4f} {minv:>8.4f} {maxv:>8.4f}")


def journal_editorial_sjr_matrix(conn):
    header("Top 5 editoriales por factor de impacto promedio")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT e."Nombre",
                   COUNT(DISTINCT j."Id") AS n_journals,
                   ROUND(AVG(f."Valor")::numeric, 4) AS avg_sjr
            FROM "Factor_Impacto" f
            JOIN "Journal" j ON j."Id" = f."Id_Journal"
            JOIN "Editorial" e ON e."Id" = j."Id_Editorial"
            WHERE j."Id_Editorial" IS NOT NULL
            GROUP BY e."Id", e."Nombre"
            ORDER BY avg_sjr DESC
            LIMIT 5
        """)
        rows = cur.fetchall()
        print(f"{'Editorial':<45s} {'Journals':>10s} {'Avg SJR':>10s}")
        print("-" * 67)
        for nombre, n, avg in rows:
            print(f"{nombre[:43]:<45s} {n:>10d} {avg:>10.4f}")


def main():
    load_env()
    conn = get_postgres_cnx()
    log.info("Connected to Postgres")

    top_10_journals_with_most_sjr_years(conn)
    sjr_coverage_by_year(conn)
    example_journal_without_sjr(conn)
    journal_editorial_sjr_matrix(conn)

    conn.close()
    log.info("Analytics done.")


if __name__ == "__main__":
    main()
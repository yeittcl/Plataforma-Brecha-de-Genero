import json
import logging
import subprocess
import sys
from pathlib import Path

from etl.common import get_postgres_cnx, load_env

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ALL_TABLES = [
    "Pais", "Region", "Area", "Categoria", "Posicion", "Area_Categoria",
    "Investigador", "Journal", "Editorial", "Factor_Impacto", "Paper", "Contribucion",
]


def header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def check_counts(conn):
    header("Conteo de tablas")
    counts = {}
    with conn.cursor() as cur:
        for table in ALL_TABLES:
            cur.execute(f"SELECT COUNT(*) FROM \"{table}\"")
            count = cur.fetchone()[0]
            counts[table] = count
            print(f"  {table:20s} {count:>15,}")
    return counts


def check_referential_integrity(conn):
    header("Integridad referencial")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM "Paper" p
            WHERE NOT EXISTS (SELECT 1 FROM "Journal" j WHERE j."Id" = p."Id_Journal")
        """)
        n = cur.fetchone()[0]
        print(f"  Papers sin Journal valido:      {n:>10,}")

        cur.execute("""
            SELECT COUNT(*) FROM "Contribucion" c
            WHERE NOT EXISTS (SELECT 1 FROM "Paper" p WHERE p."Id" = c."IdPaper")
        """)
        n = cur.fetchone()[0]
        print(f"  Contribucions con paper roto:   {n:>10,}")

        cur.execute("""
            SELECT COUNT(*) FROM "Contribucion" c
            WHERE NOT EXISTS (SELECT 1 FROM "Investigador" i WHERE i."Id" = c."IdInvestigador")
        """)
        n = cur.fetchone()[0]
        print(f"  Contribucions con invest roto:  {n:>10,}")

        cur.execute("""
            SELECT COUNT(*) FROM "Journal" j
            WHERE NOT EXISTS (SELECT 1 FROM "Editorial" e WHERE e."Id" = j."Id_Editorial")
        """)
        n = cur.fetchone()[0]
        print(f"  Journals sin Editorial:         {n:>10,}  (esperado: muchos antes de TASK-01-008)")

        cur.execute("""
            SELECT COUNT(*) FROM "Paper" p
            WHERE "Id_Journal" IS NULL OR "Id_Categoria" IS NULL
        """)
        n = cur.fetchone()[0]
        print(f"  Papers con FKs NULL criticos:   {n:>10,}")


def check_data_quality(conn):
    header("Calidad de datos")
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM \"Investigador\" WHERE \"Nombre\" = 'Unknown'")
        n = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM \"Investigador\"")
        total = cur.fetchone()[0]
        pct = (n / total * 100) if total else 0
        print(f"  Investigador 'Unknown':         {n:>10,}  ({pct:.1f}%)")

        cur.execute("""
            SELECT "Genero", COUNT(*) AS n
            FROM "Investigador"
            GROUP BY "Genero"
            ORDER BY n DESC
        """)
        print(f"  Distribucion de genero:")
        for genero, n in cur:
            pct = (n / total * 100) if total else 0
            print(f"    {genero:15s} {n:>10,}  ({pct:.1f}%)")

        cur.execute("""
            SELECT "Año", COUNT(*) AS n
            FROM "Paper"
            WHERE "Año" IS NOT NULL
            GROUP BY "Año"
            ORDER BY n DESC
            LIMIT 5
        """)
        print(f"  Top 5 anios con mas papers:")
        for anio, n in cur:
            print(f"    {anio}  {n:>10,}")

        cur.execute("""
            SELECT a."Nombre", COUNT(*) AS n
            FROM "Paper" p
            JOIN "Categoria" c ON c."Id" = p."Id_Categoria"
            JOIN "Area_Categoria" ac ON ac."IdCategoria" = c."Id"
            JOIN "Area" a ON a."Id" = ac."IdArea"
            GROUP BY a."Nombre"
            ORDER BY n DESC
        """)
        print(f"  Papers por area:")
        for area, n in cur:
            print(f"    {area:15s} {n:>10,}")

        cur.execute("""
            SELECT p."PosicionInteres", COUNT(*) AS n
            FROM "Contribucion" c
            JOIN "Posicion" p ON p."Id" = c."Id_Posicion"
            GROUP BY p."PosicionInteres"
            ORDER BY n DESC
        """)
        print(f"  Contribuciones por posicion de interes:")
        for pos, n in cur:
            print(f"    {pos:15s} {n:>10,}")


def check_performance(conn):
    header("Performance (EXPLAIN)")
    queries = [
        ("Paper por anio", 'SELECT * FROM "Paper" WHERE "Año" = 2021'),
        ("Contribucion por paper", 'SELECT * FROM "Contribucion" WHERE "IdPaper" = 1'),
        ("Contar mujeres", 'SELECT COUNT(*) FROM "Investigador" WHERE "Genero" = \'female\''),
    ]
    with conn.cursor() as cur:
        for label, q in queries:
            print(f"\n  {label}:")
            cur.execute(f"EXPLAIN {q}")
            for row in cur:
                line = "    " + row[0]
                print(line)
                if "Index" in line or "Bitmap" in line:
                    pass


def get_counts_dict(conn):
    counts = {}
    with conn.cursor() as cur:
        for table in ALL_TABLES:
            cur.execute(f"SELECT COUNT(*) FROM \"{table}\"")
            counts[table] = cur.fetchone()[0]
    return counts


def check_idempotency():
    header("Idempotencia (re-correr load_postgres.py)")
    load_env()
    conn = get_postgres_cnx()

    before = get_counts_dict(conn)
    print(f"  Conteo ANTES:")
    for table, n in before.items():
        print(f"    {table:20s} {n:>15,}")
    conn.close()

    print(f"\n  Re-corriendo load_postgres.py...")
    result = subprocess.run(
        [sys.executable, "etl/load_postgres.py"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  FAIL: load_postgres.py retorno {result.returncode}")
        print(result.stderr[-2000:])
        return False
    print(f"  load_postgres.py completo OK")

    conn = get_postgres_cnx()
    after = get_counts_dict(conn)
    print(f"\n  Conteo DESPUES:")
    for table, n in after.items():
        print(f"    {table:20s} {n:>15,}")
    conn.close()

    print(f"\n  Comparacion:")
    all_ok = True
    for table in ALL_TABLES:
        b, a = before[table], after[table]
        if b == a:
            print(f"    OK   {table:20s} estable en {a:,}")
        else:
            delta = a - b
            print(f"    FAIL {table:20s} {b:,} -> {a:,}  (delta {delta:+,})")
            all_ok = False

    return all_ok


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Memoria ETL verification")
    parser.add_argument("--skip-counts", action="store_true")
    parser.add_argument("--skip-integrity", action="store_true")
    parser.add_argument("--skip-quality", action="store_true")
    parser.add_argument("--skip-performance", action="store_true")
    parser.add_argument("--skip-idempotency", action="store_true")
    args = parser.parse_args()

    load_env()
    conn = get_postgres_cnx()
    log.info("Connected to Postgres")

    try:
        if not args.skip_counts:
            check_counts(conn)
        if not args.skip_integrity:
            check_referential_integrity(conn)
        if not args.skip_quality:
            check_data_quality(conn)
        if not args.skip_performance:
            check_performance(conn)
    finally:
        conn.close()

    if not args.skip_idempotency:
        ok = check_idempotency()
        if not ok:
            sys.exit(1)

    log.info("Verification done.")


if __name__ == "__main__":
    main()
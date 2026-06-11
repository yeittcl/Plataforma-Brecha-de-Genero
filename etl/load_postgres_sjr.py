import logging
import re
from pathlib import Path

import pandas as pd

from etl.common import get_postgres_cnx, load_env

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SJR_DIR = Path("data/external/sjr")
SEPARATOR = ";"
ENCODING = "utf-8"


def build_journal_lookup(conn):
    by_name = {}
    with conn.cursor() as cur:
        cur.execute('SELECT "Id", "Nombre" FROM "Journal"')
        for jid, nombre in cur:
            if nombre:
                by_name[nombre.strip().upper()] = jid
    log.info(f"Loaded {len(by_name)} journal names")
    return by_name


def find_journal_id(title, by_name):
    if not title:
        return None
    key = title.strip().upper()
    return by_name.get(key)


def insert_factor_impacto(conn, year, valor, jid):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO "Factor_Impacto" ("Año", "Valor", "Id_Journal")
               VALUES (%s, %s, %s)
               ON CONFLICT ("Id_Journal", "Año") DO NOTHING""",
            (year, valor, jid),
        )
        return cur.rowcount > 0


def parse_sjr_value(raw):
    if pd.isna(raw):
        return None
    s = str(raw).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_sjr_year(conn, filepath, year, by_name):
    log.info(f"Loading SJR {year}: {filepath.name}")
    df = pd.read_csv(filepath, sep=SEPARATOR, encoding=ENCODING, dtype=str)

    inserted = 0
    skipped_no_match = 0
    skipped_bad_value = 0

    for _, row in df.iterrows():
        title = row.get("Title", "")
        sjr_raw = row.get("SJR", "")

        sjr_value = parse_sjr_value(sjr_raw)
        if sjr_value is None:
            skipped_bad_value += 1
            continue

        jid = find_journal_id(title, by_name)
        if not jid:
            skipped_no_match += 1
            continue

        if insert_factor_impacto(conn, year, sjr_value, jid):
            inserted += 1

    conn.commit()
    log.info(f"  SJR {year} done: {inserted} inserted, {skipped_no_match} no-match, "
             f"{skipped_bad_value} bad-value")
    return inserted, skipped_no_match, skipped_bad_value


def main():
    load_env()
    conn = get_postgres_cnx()
    log.info("Connected to Postgres")

    by_name = build_journal_lookup(conn)

    sjr_files = sorted(SJR_DIR.glob("scimagojr *.csv"))
    log.info(f"Found {len(sjr_files)} SJR files in {SJR_DIR}")

    total_inserted = 0
    total_no_match = 0
    total_bad_value = 0
    files_loaded = 0

    for filepath in sjr_files:
        match = re.search(r"(\d{4})", filepath.name)
        if not match:
            log.warning(f"Skipping {filepath.name} (no year in name)")
            continue
        year = int(match.group(1))
        ins, no_match, bad = load_sjr_year(conn, filepath, year, by_name)
        total_inserted += ins
        total_no_match += no_match
        total_bad_value += bad
        files_loaded += 1

    conn.close()
    log.info(f"All SJR done. {files_loaded} files loaded, {total_inserted} factors inserted, "
             f"{total_no_match} no-match, {total_bad_value} bad-value")


if __name__ == "__main__":
    main()
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
    by_issn = {}
    by_name = {}
    with conn.cursor() as cur:
        cur.execute("SELECT \"Id\", \"Nombre\", \"ISSN\" FROM \"Journal\"")
        for jid, nombre, issn in cur:
            if nombre:
                by_name[nombre.strip().upper()] = jid
            if issn:
                cleaned = clean_issn(issn)
                if cleaned:
                    by_issn[cleaned] = jid
    log.info(f"Loaded {len(by_issn)} ISSN, {len(by_name)} journal names")
    return by_issn, by_name


def clean_issn(raw):
    if not raw:
        return None
    first = raw.split(",")[0].strip().upper().replace(" ", "").replace("-", "")
    return first if first else None


def find_journal_id(issn_raw, title, by_issn, by_name):
    cleaned = clean_issn(issn_raw)
    if cleaned and cleaned in by_issn:
        return by_issn[cleaned], "issn"
    if title:
        key = title.strip().upper()
        if key in by_name:
            return by_name[key], "name"
    return None, None


def get_journal_issn(conn, jid):
    with conn.cursor() as cur:
        cur.execute("SELECT \"ISSN\" FROM \"Journal\" WHERE \"Id\" = %s", (jid,))
        row = cur.fetchone()
        return row[0] if row else None


def update_journal_issn(conn, jid, issn_raw):
    cleaned = clean_issn(issn_raw)
    if not cleaned:
        return False
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE \"Journal\" SET \"ISSN\" = %s WHERE \"Id\" = %s AND \"ISSN\" IS NULL",
            (cleaned, jid),
        )
        return cur.rowcount > 0


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


def load_sjr_year(conn, filepath, year, by_issn, by_name):
    log.info(f"Loading SJR {year}: {filepath.name}")
    df = pd.read_csv(filepath, sep=SEPARATOR, encoding=ENCODING, dtype=str)

    inserted = 0
    skipped_no_match = 0
    skipped_bad_value = 0
    issn_backfilled = 0

    for _, row in df.iterrows():
        title = row.get("Title", "")
        issn_raw = row.get("Issn", "")
        sjr_raw = row.get("SJR", "")

        sjr_value = parse_sjr_value(sjr_raw)
        if sjr_value is None:
            skipped_bad_value += 1
            continue

        jid, match_type = find_journal_id(issn_raw, title, by_issn, by_name)
        if not jid:
            skipped_no_match += 1
            continue

        if match_type == "name":
            current_issn = get_journal_issn(conn, jid)
            if not current_issn and issn_raw:
                cleaned = clean_issn(issn_raw)
                if cleaned:
                    if update_journal_issn(conn, jid, cleaned):
                        issn_backfilled += 1
                        by_issn[cleaned] = jid

        if insert_factor_impacto(conn, year, sjr_value, jid):
            inserted += 1

    conn.commit()
    log.info(f"  SJR {year} done: {inserted} inserted, {skipped_no_match} no-match, "
             f"{skipped_bad_value} bad-value, {issn_backfilled} ISSN backfilled")
    return inserted, skipped_no_match, skipped_bad_value, issn_backfilled


def main():
    load_env()
    conn = get_postgres_cnx()
    log.info("Connected to Postgres")

    by_issn, by_name = build_journal_lookup(conn)

    sjr_files = sorted(SJR_DIR.glob("scimagojr *.csv"))
    log.info(f"Found {len(sjr_files)} SJR files in {SJR_DIR}")

    total_inserted = 0
    total_no_match = 0
    total_bad_value = 0
    total_issn_backfilled = 0
    files_loaded = 0

    for filepath in sjr_files:
        match = re.search(r"(\d{4})", filepath.name)
        if not match:
            log.warning(f"Skipping {filepath.name} (no year in name)")
            continue
        year = int(match.group(1))
        ins, no_match, bad, issn = load_sjr_year(conn, filepath, year, by_issn, by_name)
        total_inserted += ins
        total_no_match += no_match
        total_bad_value += bad
        total_issn_backfilled += issn
        files_loaded += 1

    conn.close()
    log.info(f"All SJR done. {files_loaded} files loaded, {total_inserted} factors inserted, "
             f"{total_no_match} no-match, {total_bad_value} bad-value, "
             f"{total_issn_backfilled} ISSN backfilled")


if __name__ == "__main__":
    main()
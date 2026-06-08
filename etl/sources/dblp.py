import logging

import pandas as pd

from etl.common import normalize_firstname, normalize_position
from etl.postgres_helpers import ensure_investigador, ensure_journal, ensure_paper_by_natural_key, insert_contribucion

log = logging.getLogger(__name__)

CHUNK_SIZE = 10_000


def load_dblp(conn, filepath, categoria_lookup, posicion_lookup, gender_map, journal_lookup):
    log.info(f"Loading DBLP: {filepath}")
    cat_cs = categoria_lookup.get("Computer", categoria_lookup.get("CS"))
    if not cat_cs:
        log.warning("CS/Computer categoria not found, skipping DBLP")
        return 0

    prev_key = None
    paper_id = None
    authors_in_paper = []
    processed_papers = 0

    for chunk in pd.read_csv(
        filepath,
        header=0,
        chunksize=CHUNK_SIZE,
        names=["key", "order", "journal", "title", "year", "ee",
               "positionpaper", "orcid", "name", "firstname", "lastname", "disambiguation"],
    ):
        for _, row in chunk.iterrows():
            key = str(row["key"]).strip() if not pd.isna(row["key"]) else None
            if not key:
                continue

            journal_name = str(row["journal"]).strip() if not pd.isna(row["journal"]) else None
            title = str(row["title"]).strip() if not pd.isna(row["title"]) else None
            year = int(float(row["year"])) if not pd.isna(row["year"]) else None

            if key != prev_key:
                if authors_in_paper and paper_id:
                    for (fn_key, pos_ord, pos_int) in authors_in_paper:
                        gen, prob = gender_map.get(fn_key, ("unknown", 0.5))
                        inv_id = ensure_investigador(conn, fn_key, gen, prob)
                        insert_contribucion(conn, paper_id, inv_id, pos_ord, pos_int, posicion_lookup)
                    processed_papers += 1
                    conn.commit()

                jid = ensure_journal(conn, journal_name, journal_lookup) if journal_name else None
                pid_paper = ensure_paper_by_natural_key(
                    conn, title, year, journal_name, jid, cat_cs, None, journal_lookup,
                )
                paper_id = pid_paper
                authors_in_paper = []
                prev_key = key

            if paper_id:
                firstname = str(row["firstname"]).strip() if not pd.isna(row["firstname"]) else "Unknown"
                pos_paper = str(row["positionpaper"]).strip().lower() if not pd.isna(row["positionpaper"]) else "other"
                pos_interes = normalize_position(pos_paper)
                fn_key = normalize_firstname(firstname)
                order_ordinal = int(row["order"]) if not pd.isna(row["order"]) else len(authors_in_paper)
                authors_in_paper.append((fn_key, order_ordinal, pos_interes))

        log.info(f"  DBLP chunk: {processed_papers} papers processed")

    if authors_in_paper and paper_id:
        for (fn_key, pos_ord, pos_int) in authors_in_paper:
            gen, prob = gender_map.get(fn_key, ("unknown", 0.5))
            inv_id = ensure_investigador(conn, fn_key, gen, prob)
            insert_contribucion(conn, paper_id, inv_id, pos_ord, pos_int, posicion_lookup)
        processed_papers += 1
        conn.commit()

    log.info(f"DBLP done: {processed_papers} papers")
    return processed_papers
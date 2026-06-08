import json
import logging

import pandas as pd

from etl.common import normalize_firstname
from etl.postgres_helpers import ensure_investigador, ensure_journal, ensure_paper_by_pmid, insert_contribucion

log = logging.getLogger(__name__)

CHUNK_SIZE = 10_000


def load_pubmed(conn, filepath, categoria_lookup, posicion_lookup, gender_map, journal_lookup):
    log.info(f"Loading PubMed: {filepath}")
    cat_bio = categoria_lookup.get("Biology", categoria_lookup.get("BIO"))
    if not cat_bio:
        log.warning("BIO/Biology categoria not found, skipping PubMed")
        return 0

    processed_papers = 0

    for chunk in pd.read_csv(filepath, header=0, chunksize=CHUNK_SIZE):
        for _, row in chunk.iterrows():
            pubmed_id = str(row["pubmed_id"]).strip() if not pd.isna(row["pubmed_id"]) else None
            if not pubmed_id:
                continue

            title = str(row["title"]).strip() if not pd.isna(row["title"]) else None
            doi = str(row["doi"]).strip() if not pd.isna(row["doi"]) else None

            pub_date = str(row["publication_date"]) if not pd.isna(row["publication_date"]) else None
            year = None
            if pub_date:
                try:
                    year = int(pub_date[:4])
                except Exception:
                    year = None

            journal_name = str(row["journal"]).strip() if not pd.isna(row["journal"]) else None
            mesh_cat = str(row["Mesh"]).strip() if not pd.isna(row["Mesh"]) else None
            cat_row_id = categoria_lookup.get(mesh_cat, cat_bio) if mesh_cat else cat_bio

            jid = ensure_journal(conn, journal_name, journal_lookup) if journal_name else None
            paper_id = ensure_paper_by_pmid(
                conn, pubmed_id, doi, title, year, jid, cat_row_id, None, journal_lookup,
            )
            if not paper_id:
                continue

            processed_papers += 1

            authors_str = str(row["authors"]) if not pd.isna(row["authors"]) else "[]"
            try:
                authors_list = json.loads(authors_str)
            except Exception:
                authors_list = []

            total_authors = len(authors_list)
            if total_authors == 0:
                continue

            last_idx = total_authors - 1
            for idx, author in enumerate(authors_list):
                firstname = str(
                    author.get("firstname", author.get("first_name", ""))
                ).strip()
                if not firstname:
                    firstname = "Unknown"
                fn_key = normalize_firstname(firstname)
                gen, prob = gender_map.get(fn_key, ("unknown", 0.5))
                inv_id = ensure_investigador(conn, fn_key, gen, prob)

                if total_authors == 1:
                    pos_interes = "first"
                elif idx == 0:
                    pos_interes = "first"
                elif idx == last_idx:
                    pos_interes = "last"
                elif idx == 1:
                    pos_interes = "second"
                else:
                    pos_interes = "other"

                insert_contribucion(conn, paper_id, inv_id, idx, pos_interes, posicion_lookup)

        conn.commit()
        log.info(f"  PubMed chunk: {processed_papers} papers processed")

    log.info(f"PubMed done: {processed_papers} papers")
    return processed_papers
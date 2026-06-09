import logging
from pathlib import Path

import pandas as pd

from etl.common import normalize_country
from etl.postgres_helpers import ensure_journal, ensure_paper_by_doi

log = logging.getLogger(__name__)

CHUNK_SIZE = 10_000


def _read_csv(csv_path, has_bad_first_col=False):
    if has_bad_first_col:
        return pd.read_csv(
            csv_path,
            header=0,
            skiprows=0,
            usecols=["id", "year", "idpublication", "typepublication", "country", "journal", "category"],
            dtype=str,
        )
    return pd.read_csv(
        csv_path,
        header=0,
        usecols=["id", "year", "idpublication", "typepublication", "country", "journal", "category"],
        dtype=str,
    )


def load_paper_area(conn, area, paper_path, categoria_lookup, pais_lookup, journal_lookup, has_bad_first_col=False):
    log.info(f"Loading papers: {paper_path} (area={area})")
    if not Path(paper_path).exists():
        log.warning(f"Paper file not found: {paper_path}")
        return {}

    id_to_paper_id = {}
    row_count = 0
    skipped_no_category = 0
    skipped_no_country = 0
    inserted = 0

    for chunk in pd.read_csv(
        paper_path,
        header=0,
        chunksize=CHUNK_SIZE,
        usecols=["id", "year", "idpublication", "typepublication", "country", "journal", "category"],
        dtype=str,
        on_bad_lines="skip",
    ):
        if has_bad_first_col and chunk.columns[0] != "id":
            chunk.columns = ["id", "year", "idpublication", "typepublication", "country", "journal", "category"]

        for _, row in chunk.iterrows():
            row_count += 1
            row_id = str(row.get("id", "")).strip() if not pd.isna(row.get("id")) else ""
            doi = str(row.get("idpublication", "")).strip() if not pd.isna(row.get("idpublication")) else ""
            category = str(row.get("category", "")).strip() if not pd.isna(row.get("category")) else ""
            journal_name = str(row.get("journal", "")).strip() if not pd.isna(row.get("journal")) else ""
            country_raw = str(row.get("country", "")).strip() if not pd.isna(row.get("country")) else ""
            year_str = str(row.get("year", "")).strip() if not pd.isna(row.get("year")) else ""

            if not row_id:
                continue

            try:
                year = int(float(year_str)) if year_str else None
            except (ValueError, TypeError):
                year = None
            if not year:
                continue

            cat_id = categoria_lookup.get(category) if category else None
            if not cat_id:
                skipped_no_category += 1
                continue

            country = normalize_country(country_raw)
            pais_id = pais_lookup.get(country, pais_lookup.get("UNKNOWN"))
            if country == "Unknown" or not pais_id:
                skipped_no_country += 1

            jid = ensure_journal(conn, journal_name, journal_lookup)

            paper_id = None
            if doi:
                paper_id = ensure_paper_by_doi(conn, doi, year, jid, cat_id, pais_id)
                if paper_id:
                    inserted += 1
                    id_to_paper_id[row_id] = (doi, paper_id)

        if row_count % 50_000 == 0:
            log.info(f"  Paper {area}: {row_count} rows, {inserted} papers, "
                     f"{skipped_no_category} no-category, {skipped_no_country} no-country")

    conn.commit()
    log.info(f"  Paper {area} done: {row_count} rows, {inserted} papers inserted, "
             f"{skipped_no_category} no-category, {skipped_no_country} no-country")
    return id_to_paper_id
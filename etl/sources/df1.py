import logging

import pandas as pd

from etl.common import normalize_country, progress_bar
from etl.postgres_helpers import ensure_journal, ensure_paper_by_doi

log = logging.getLogger(__name__)

CHUNK_SIZE = 10_000


def load_df1(conn, filepath, area_nombre, categoria_lookup, pais_lookup, journal_lookup):
    log.info(f"Loading DF1: {filepath} (area={area_nombre})")
    cat_id = categoria_lookup.get(area_nombre)
    if not cat_id:
        log.warning(f"Area {area_nombre} not found in Categoria, skipping")
        return {}, {}

    doi_to_paper_id = {}
    counter_area_to_doi = {}
    seen_counter_area = set()
    row_count = 0

    for chunk in pd.read_csv(
        filepath,
        header=None,
        chunksize=CHUNK_SIZE,
        names=["id", "Year", "DOI", "DOI_type", "Country", "Journal", "mesh_major"],
    ):
        for _, row in chunk.iterrows():
            row_count += 1
            row_id = str(row["id"]) if not pd.isna(row["id"]) else None
            doi = str(row["DOI"]).strip() if not pd.isna(row["DOI"]) else None
            if not doi or not row_id:
                continue

            parts = row_id.split("-")
            if len(parts) >= 3:
                counter_area = parts[0] + "-" + parts[1]
            else:
                counter_area = row_id.rsplit("-", 1)[0] if "-" in row_id else row_id

            if counter_area not in seen_counter_area:
                seen_counter_area.add(counter_area)
                counter_area_to_doi[counter_area] = doi

            year = int(row["Year"]) if not pd.isna(row["Year"]) else None
            if not year:
                continue

            country = normalize_country(str(row["Country"]) if not pd.isna(row["Country"]) else "")
            pais_id = pais_lookup.get(country, pais_lookup.get("UNKNOWN"))

            journal_name = str(row["Journal"]).strip() if not pd.isna(row["Journal"]) else None
            jid = ensure_journal(conn, journal_name, journal_lookup) if journal_name else None

            mesh_cat = str(row["mesh_major"]).strip() if not pd.isna(row["mesh_major"]) else area_nombre
            cat_row_id = categoria_lookup.get(mesh_cat, cat_id)

            title = f"Paper-{doi}"
            paper_id = ensure_paper_by_doi(conn, doi, title, year, jid, cat_row_id, pais_id, journal_lookup)
            if paper_id:
                doi_to_paper_id[doi] = paper_id

        if row_count % 50_000 == 0:
            log.info(f"  DF1 {area_nombre}: {row_count} rows, {len(doi_to_paper_id)} papers, "
                     f"{len(counter_area_to_doi)} counter-area groups")

    conn.commit()
    log.info(f"  DF1 {area_nombre} done: {row_count} rows, {len(doi_to_paper_id)} papers, "
             f"{len(counter_area_to_doi)} counter-area groups")
    return doi_to_paper_id, counter_area_to_doi
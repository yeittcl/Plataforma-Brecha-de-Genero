import logging
from pathlib import Path

from etl.common import get_postgres_cnx, load_env
from etl.load_gender import load_gender_lookup
from etl.postgres_helpers import build_lookups
from etl.sources.df1 import load_df1
from etl.sources.df2 import load_df2
from etl.sources.dblp import load_dblp
from etl.sources.pubmed import load_pubmed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main():
    load_env()
    conn = get_postgres_cnx()
    log.info("Connected to Postgres")

    pais_lookup, categoria_lookup, posicion_lookup, journal_lookup = build_lookups(conn)
    gender_map = load_gender_lookup()

    doi_to_paper_id = {}
    counter_area_to_doi = {}

    df1_configs = [
        ("data/raw/df1_chem.csv", "CHEM"),
        ("data/raw/df1_earth.csv", "EARTH"),
        ("data/raw/df1_phys.csv", "PHYS"),
    ]
    for filepath, area in df1_configs:
        if Path(filepath).exists():
            m, ca = load_df1(
                conn, filepath, area,
                categoria_lookup, pais_lookup, journal_lookup,
            )
            doi_to_paper_id.update(m)
            counter_area_to_doi.update(ca)
        else:
            log.warning(f"DF1 file not found: {filepath}")

    df2_path = "data/raw/df2_norepeated.csv"
    if Path(df2_path).exists():
        load_df2(
            conn, df2_path,
            posicion_lookup, gender_map,
            doi_to_paper_id, counter_area_to_doi,
        )
    else:
        log.warning(f"DF2 file not found: {df2_path}")

    dblp_path = "data/raw/dblp_authors.csv"
    if Path(dblp_path).exists():
        load_dblp(
            conn, dblp_path,
            categoria_lookup, posicion_lookup, gender_map, journal_lookup,
        )
    else:
        log.warning(f"DBLP file not found: {dblp_path}")

    pubmed_path = "data/raw/pubmed_articles.csv"
    if Path(pubmed_path).exists():
        load_pubmed(
            conn, pubmed_path,
            categoria_lookup, posicion_lookup, gender_map, journal_lookup,
        )
    else:
        log.warning(f"PubMed file not found: {pubmed_path}")

    conn.commit()
    conn.close()
    log.info("All sources loaded. Done.")


if __name__ == "__main__":
    main()
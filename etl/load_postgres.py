import logging
from pathlib import Path

from etl.common import get_postgres_cnx, load_env
from etl.postgres_helpers import build_lookups
from etl.sources.autor import load_autor_area
from etl.sources.paper import load_paper_area

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

AREAS = ["BIO", "CS", "CHEM", "PHYS", "EARTH"]

CS_PAPER_BAD_FIRST_COL = True


def main():
    load_env()
    conn = get_postgres_cnx()
    log.info("Connected to Postgres")

    pais_lookup, categoria_lookup, posicion_lookup, journal_lookup = build_lookups(conn)

    for area in AREAS:
        paper_path = f"data/raw/rawPaper/{area}_paper.csv"
        autor_path = f"data/raw/rawAutor/{area}_autor.csv"

        has_bad_col = (area == "CS")

        log.info(f"=== Area: {area} ===")
        id_to_paper_id = load_paper_area(
            conn, area, paper_path,
            categoria_lookup, pais_lookup, journal_lookup,
            has_bad_first_col=has_bad_col,
        )
        load_autor_area(
            conn, area, autor_path,
            id_to_paper_id, posicion_lookup,
        )

    conn.commit()
    conn.close()
    log.info("All sources loaded. Done.")


if __name__ == "__main__":
    main()
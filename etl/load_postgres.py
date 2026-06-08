import logging
import sys

from etl.common import get_postgres_cnx, load_env
from etl.postgres_helpers import build_lookups
from etl.sources.autor import load_autor_area
from etl.sources.paper import load_paper_area

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

AREAS = ["BIO", "CS", "CHEM", "PHYS", "EARTH"]


def main():
    areas = sys.argv[1:] if len(sys.argv) > 1 else AREAS
    areas = [a.upper() for a in areas]

    for a in areas:
        if a not in AREAS:
            log.error(f"Unknown area '{a}'. Valid: {AREAS}")
            sys.exit(1)

    load_env()
    conn = get_postgres_cnx()
    log.info(f"Connected to Postgres. Will process: {areas}")

    pais_lookup, categoria_lookup, posicion_lookup, journal_lookup = build_lookups(conn)

    for area in areas:
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
    log.info(f"Areas {areas} loaded. Done.")


if __name__ == "__main__":
    main()
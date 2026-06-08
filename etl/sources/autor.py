import logging
from pathlib import Path

import pandas as pd

from etl.common import normalize_firstname, normalize_position
from etl.postgres_helpers import ensure_investigador, insert_contribucion

log = logging.getLogger(__name__)

CHUNK_SIZE = 10_000


def _extract_position_from_id(row_id):
    parts = row_id.split("-")
    if len(parts) >= 3:
        return parts[-1] if parts[-1].isdigit() else "0"
    return "0"


def load_autor_area(conn, area, autor_path, id_to_paper_id, posicion_lookup):
    log.info(f"Loading authors: {autor_path} (area={area})")
    if not Path(autor_path).exists():
        log.warning(f"Autor file not found: {autor_path}")
        return 0, 0

    row_count = 0
    inserted = 0
    skipped_no_paper = 0
    skipped_invalid_position = 0
    seen_dois = {}

    for chunk in pd.read_csv(
        autor_path,
        header=0,
        chunksize=CHUNK_SIZE,
        usecols=["id", "name", "gender", "probability", "position"],
        dtype=str,
        on_bad_lines="skip",
    ):
        for _, row in chunk.iterrows():
            row_count += 1
            row_id = str(row.get("id", "")).strip() if not pd.isna(row.get("id")) else ""
            name = str(row.get("name", "")).strip() if not pd.isna(row.get("name")) else ""
            gender = str(row.get("gender", "")).strip().lower() if not pd.isna(row.get("gender")) else "unknown"
            prob_str = str(row.get("probability", "0")).strip() if not pd.isna(row.get("probability")) else "0"
            position_label = str(row.get("position", "")).strip() if not pd.isna(row.get("position")) else "other"

            if not row_id:
                continue

            if row_id not in id_to_paper_id:
                skipped_no_paper += 1
                continue

            doi, paper_id = id_to_paper_id[row_id]

            try:
                probabilidad = float(prob_str) if prob_str else 0.5
            except (ValueError, TypeError):
                probabilidad = 0.5

            genero = gender if gender in ("male", "female", "unknown") else "unknown"

            firstname = normalize_firstname(name)
            inv_id = ensure_investigador(conn, firstname, genero, probabilidad)

            pos_interes = normalize_position(position_label)
            order_pos_str = _extract_position_from_id(row_id)
            try:
                order_pos = int(order_pos_str)
            except ValueError:
                order_pos = 0

            insert_contribucion(conn, paper_id, inv_id, order_pos, pos_interes, posicion_lookup)
            inserted += 1

        if row_count % 50_000 == 0:
            log.info(f"  Autor {area}: {row_count} rows, {inserted} inserted, {skipped_no_paper} no-paper")

    conn.commit()
    log.info(f"  Autor {area} done: {row_count} rows, {inserted} inserted, {skipped_no_paper} no-paper")
    return inserted, skipped_no_paper
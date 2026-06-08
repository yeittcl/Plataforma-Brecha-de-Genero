import logging

import pandas as pd

from etl.common import normalize_firstname, normalize_position, progress_bar
from etl.postgres_helpers import ensure_investigador, insert_contribucion

log = logging.getLogger(__name__)

CHUNK_SIZE = 10_000


def load_df2(conn, filepath, posicion_lookup, gender_map,
             doi_to_paper_id, counter_area_to_doi):
    log.info(f"Loading DF2: {filepath}")
    skipped = 0
    processed = 0

    for chunk in pd.read_csv(
        filepath,
        header=0,
        chunksize=CHUNK_SIZE,
        names=["id", "name", "gender", "probability", "count", "position"],
    ):
        for _, row in chunk.iterrows():
            row_id = str(row["id"]) if not pd.isna(row["id"]) else None
            if not row_id:
                skipped += 1
                continue

            parts = row_id.split("-")
            if len(parts) < 3:
                skipped += 1
                continue

            counter_area = parts[0] + "-" + parts[1]
            doi = counter_area_to_doi.get(counter_area)

            if not doi or doi not in doi_to_paper_id:
                skipped += 1
                continue

            processed += 1
            paper_id = doi_to_paper_id[doi]

            firstname = str(row["name"]).strip() if not pd.isna(row["name"]) else "Unknown"
            genero = str(row["gender"]).strip().lower() if not pd.isna(row["gender"]) else "unknown"
            probabilidad = float(row["probability"]) if not pd.isna(row["probability"]) else 0.5

            fn_key = normalize_firstname(firstname)
            gen, prob = gender_map.get(fn_key, (genero, probabilidad))
            inv_id = ensure_investigador(conn, fn_key, gen, prob)

            pos_interes = normalize_position(str(row["position"]) if not pd.isna(row["position"]) else "other")
            order_pos = int(parts[-1]) if parts[-1].isdigit() else 0
            insert_contribucion(conn, paper_id, inv_id, order_pos, pos_interes, posicion_lookup)

        conn.commit()

    conn.commit()
    log.info(f"DF2 done: {processed} processed, {skipped} skipped (no counter-area match)")
    return processed, skipped
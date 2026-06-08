import logging

import pandas as pd

log = logging.getLogger(__name__)

CHUNK_SIZE = 100_000


def load_gender_lookup(filepath="data/raw/gender_lookup.csv"):
    log.info("Loading gender_lookup.csv (this may take a minute)...")
    gender_map = {}
    chunks = pd.read_csv(
        filepath,
        header=0,
        chunksize=CHUNK_SIZE,
        dtype={"firstname": str, "genero": str, "probabilidad": float},
        on_bad_lines="skip",
    )
    for chunk in chunks:
        for _, row in chunk.iterrows():
            fn = row["firstname"]
            if pd.isna(fn) or not str(fn).strip():
                continue
            key = str(fn).strip().title()
            if key not in gender_map:
                gender_map[key] = (
                    row["genero"],
                    float(row["probabilidad"]) if not pd.isna(row["probabilidad"]) else 0.5,
                )
    log.info(f"Gender lookup: {len(gender_map)} entries")
    return gender_map
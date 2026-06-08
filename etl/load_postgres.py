import json
import logging
import sys
from pathlib import Path

import pandas as pd
import psycopg

from etl.common import (
    get_postgres_cnx,
    load_env,
    normalize_country,
    normalize_firstname,
    normalize_position,
    progress_bar,
    truncate,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CHUNK_SIZE = 10_000
GENDER_CHUNK_SIZE = 100_000

def build_lookups(conn):
    pais_lookup = {}
    with conn.cursor() as cur:
        cur.execute("SELECT \"Id\", \"Nombre\" FROM \"Pais\"")
        for row in cur:
            pais_lookup[row[1].upper()] = row[0]
    log.info(f"Loaded {len(pais_lookup)} pais")

    categoria_lookup = {}
    with conn.cursor() as cur:
        cur.execute("SELECT \"Id\", \"Nombre\" FROM \"Categoria\"")
        for row in cur:
            categoria_lookup[row[1]] = row[0]
    log.info(f"Loaded {len(categoria_lookup)} categoria")

    posicion_lookup = {}
    with conn.cursor() as cur:
        cur.execute("SELECT \"Id\", \"PosicionInteres\" FROM \"Posicion\"")
        for row in cur:
            posicion_lookup[row[1]] = row[0]
    log.info(f"Loaded {len(posicion_lookup)} posicion")

    journal_lookup = {}
    with conn.cursor() as cur:
        cur.execute("SELECT \"Id\", \"Nombre\" FROM \"Journal\"")
        for row in cur:
            journal_lookup[row[1].upper()] = row[0]
    log.info(f"Loaded {len(journal_lookup)} journal (existing)")

    return pais_lookup, categoria_lookup, posicion_lookup, journal_lookup


def ensure_journal(conn, journal_name, journal_lookup):
    if not journal_name or not journal_name.strip():
        return None
    key = journal_name.strip().upper()
    if key in journal_lookup:
        return journal_lookup[key]
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO \"Journal\" (\"Nombre\") VALUES (%s) ON CONFLICT (\"Nombre\") DO NOTHING RETURNING \"Id\"",
            (truncate(journal_name.strip(), 500),),
        )
        row = cur.fetchone()
        if row:
            jid = row[0]
            journal_lookup[key] = jid
            return jid
        cur.execute("SELECT \"Id\" FROM \"Journal\" WHERE \"Nombre\" = %s", (journal_name.strip(),))
        row = cur.fetchone()
        if row:
            journal_lookup[key] = row[0]
            return row[0]
    return None


def ensure_paper_by_doi(conn, doi, title, year, id_journal, id_categoria, id_pais, journal_lookup):
    if not doi or not doi.strip():
        return None
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO "Paper" ("Titulo", "Anio", "doi", "Id_Journal", "Id_Categoria", "Id_Pais")
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (doi) DO NOTHING
               RETURNING "Id" """,
            (truncate(title.strip() if title else "Untitled", 1000), year, doi.strip(), id_journal, id_categoria, id_pais),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("SELECT \"Id\" FROM \"Paper\" WHERE doi = %s", (doi.strip(),))
        row = cur.fetchone()
        return row[0] if row else None


def ensure_paper_by_pmid(conn, pubmed_id, doi, title, year, id_journal, id_categoria, id_pais, journal_lookup):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO "Paper" ("Titulo", "Anio", "doi", "Id_Journal", "Id_Categoria", "Id_Pais")
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (doi) DO NOTHING
               RETURNING "Id" """,
            (truncate(title.strip() if title else "Untitled", 1000), year, doi if doi else None, id_journal, id_categoria, id_pais),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        if doi:
            cur.execute("SELECT \"Id\" FROM \"Paper\" WHERE doi = %s", (doi,))
            row = cur.fetchone()
            if row:
                return row[0]
        cur.execute("SELECT \"Id\" FROM \"Paper\" WHERE \"Titulo\" = %s AND \"Anio\" = %s AND \"Id_Journal\" = %s",
                    (title.strip() if title else None, year, id_journal))
        row = cur.fetchone()
        return row[0] if row else None


def ensure_paper_by_natural_key(conn, title, year, journal_name, id_journal, id_categoria, id_pais, journal_lookup):
    if not title:
        return None
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO "Paper" ("Titulo", "Anio", "Id_Journal", "Id_Categoria", "Id_Pais")
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT ("Titulo", "Anio", "Id_Journal") DO NOTHING
               RETURNING "Id" """,
            (truncate(title.strip(), 1000), year, id_journal, id_categoria, id_pais),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "SELECT \"Id\" FROM \"Paper\" WHERE \"Titulo\" = %s AND \"Anio\" = %s AND \"Id_Journal\" = %s",
            (title.strip(), year, id_journal),
        )
        row = cur.fetchone()
        return row[0] if row else None


def ensure_investigador(conn, firstname, genero, probabilidad):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO "Investigador" ("Nombre", "Genero", "Probabilidad")
               VALUES (%s, %s, %s)
               ON CONFLICT ("Nombre") DO NOTHING
               RETURNING "Id" """,
            (truncate(firstname, 200), genero, probabilidad),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("SELECT \"Id\" FROM \"Investigador\" WHERE \"Nombre\" = %s", (firstname,))
        row = cur.fetchone()
        return row[0] if row else None


def insert_contribucion(conn, id_paper, id_investigador, posicion_ordinal, posicion_interes, posicion_lookup):
    pid = posicion_lookup.get(posicion_interes)
    if not pid:
        pid = posicion_lookup.get("other")
    if not pid:
        return
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO "Contribucion" ("IdPaper", "IdInvestigador", "PosicionOrdinal", "Id_Posicion")
               VALUES (%s, %s, %s, %s)
               ON CONFLICT ("IdPaper", "IdInvestigador", "PosicionOrdinal") DO NOTHING""",
            (id_paper, id_investigador, posicion_ordinal, pid),
        )


def load_gender_lookup():
    log.info("Loading gender_lookup.csv (this may take a minute)...")
    gender_map = {}
    chunks = pd.read_csv(
        "data/raw/gender_lookup.csv",
        header=None,
        names=["firstname", "genero", "probabilidad"],
        chunksize=GENDER_CHUNK_SIZE,
        dtype={"firstname": str, "genero": str, "probabilidad": float},
    )
    for chunk in chunks:
        for _, row in chunk.iterrows():
            fn = row["firstname"]
            if pd.isna(fn) or not str(fn).strip():
                continue
            key = str(fn).strip().title()
            if key not in gender_map:
                gender_map[key] = (row["genero"], float(row["probabilidad"]) if not pd.isna(row["probabilidad"]) else 0.5)
    log.info(f"Gender lookup: {len(gender_map)} entries")
    return gender_map


def load_df1(conn, filepath, area_nombre, categoria_lookup, pais_lookup, posicion_lookup, gender_map, journal_lookup):
    log.info(f"Loading DF1: {filepath} (area={area_nombre})")
    cat_id = categoria_lookup.get(area_nombre)
    if not cat_id:
        log.warning(f"Area {area_nombre} not found in Categoria, skipping")
        return {}, {}

    doi_to_paper_id = {}
    counter_area_to_doi = {}
    seen_counter_area = set()
    row_count = 0

    for chunk in pd.read_csv(filepath, header=None, chunksize=CHUNK_SIZE,
                              names=["id","Year","DOI","DOI_type","Country","Journal","mesh_major"]):
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
            if not paper_id:
                continue
            doi_to_paper_id[doi] = paper_id

            order_pos = int(parts[-1]) if parts[-1].isdigit() else 0
            pos_interes = normalize_position(parts[-1] if len(parts) >= 3 else "other")

            firstname = parts[1] if len(parts) >= 2 else "Unknown"
            gen, prob = gender_map.get(normalize_firstname(firstname), ("unknown", 0.5))
            inv_id = ensure_investigador(conn, normalize_firstname(firstname), gen, prob)
            insert_contribucion(conn, paper_id, inv_id, order_pos, pos_interes, posicion_lookup)

        if row_count % 50_000 == 0:
            log.info(f"  DF1 {area_nombre}: {row_count} rows, {len(doi_to_paper_id)} papers, {len(counter_area_to_doi)} groups")

    conn.commit()
    log.info(f"  DF1 {area_nombre} done: {row_count} rows, {len(doi_to_paper_id)} papers, {len(counter_area_to_doi)} counter-area groups")
    return doi_to_paper_id, counter_area_to_doi


def load_df2(conn, filepath, pais_lookup, posicion_lookup, gender_map, doi_to_paper_id, counter_area_to_doi):
    log.info(f"Loading DF2: {filepath}")
    skipped = 0
    processed = 0

    for chunk in pd.read_csv(filepath, header=0, chunksize=CHUNK_SIZE,
                              names=["id","name","gender","probability","count","position"]):
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
            pos_interes = normalize_position(str(row["position"]) if not pd.isna(row["position"]) else "other")
            firstname = str(row["name"]).strip() if not pd.isna(row["name"]) else "Unknown"
            genero = str(row["gender"]).strip().lower() if not pd.isna(row["gender"]) else "unknown"
            probabilidad = float(row["probability"]) if not pd.isna(row["probability"]) else 0.5

            fn_key = normalize_firstname(firstname)
            gen, prob = gender_map.get(fn_key, (genero, probabilidad))
            inv_id = ensure_investigador(conn, fn_key, gen, prob)

            order_pos = int(parts[-1]) if parts[-1].isdigit() else 0
            insert_contribucion(conn, paper_id, inv_id, order_pos, pos_interes, posicion_lookup)

        conn.commit()

    conn.commit()
    log.info(f"DF2 done: {processed} processed, {skipped} skipped (no counter-area match)")


def load_dblp(conn, filepath, pais_lookup, categoria_lookup, posicion_lookup, gender_map, journal_lookup):
    log.info(f"Loading DBLP: {filepath}")
    cat_cs = categoria_lookup.get("Computer", categoria_lookup.get("CS"))
    if not cat_cs:
        log.warning("CS/Computer categoria not found, skipping DBLP")
        return

    prev_key = None
    paper_id = None
    authors_in_paper = []
    pos_counter = 0
    processed_papers = 0

    for chunk in pd.read_csv(filepath, header=0, chunksize=CHUNK_SIZE,
                              names=["key","order","journal","title","year","ee","positionpaper","orcid","name","firstname","lastname","disambiguation"]):
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
                elif authors_in_paper:
                    pass

                jid = ensure_journal(conn, journal_name, journal_lookup) if journal_name else None
                pid_paper = ensure_paper_by_natural_key(conn, title, year, journal_name, jid, cat_cs, None, journal_lookup)
                paper_id = pid_paper
                authors_in_paper = []
                pos_counter = 0
                prev_key = key

            if paper_id:
                firstname = str(row["firstname"]).strip() if not pd.isna(row["firstname"]) else "Unknown"
                pos_paper = str(row["positionpaper"]).strip().lower() if not pd.isna(row["positionpaper"]) else "other"
                pos_interes = normalize_position(pos_paper)
                fn_key = normalize_firstname(firstname)
                authors_in_paper.append((fn_key, pos_counter, pos_interes))
                pos_counter += 1

        conn.commit()
        log.info(f"  DBLP chunk: {processed_papers} papers processed")

    if authors_in_paper and paper_id:
        for (fn_key, pos_ord, pos_int) in authors_in_paper:
            gen, prob = gender_map.get(fn_key, ("unknown", 0.5))
            inv_id = ensure_investigador(conn, fn_key, gen, prob)
            insert_contribucion(conn, paper_id, inv_id, pos_ord, pos_int, posicion_lookup)
        processed_papers += 1
        conn.commit()

    log.info(f"DBLP done: {processed_papers} papers")


def load_pubmed(conn, filepath, pais_lookup, categoria_lookup, posicion_lookup, gender_map, journal_lookup):
    log.info(f"Loading PubMed: {filepath}")
    cat_bio = categoria_lookup.get("Biology", categoria_lookup.get("BIO"))
    if not cat_bio:
        log.warning("BIO/Biology categoria not found, skipping PubMed")
        return

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
            paper_id = ensure_paper_by_pmid(conn, pubmed_id, doi, title, year, jid, cat_row_id, None, journal_lookup)
            if not paper_id:
                continue

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
                firstname = str(author.get("firstname", author.get("first_name", ""))).strip()
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
        log.info(f"  PubMed chunk committed")

    log.info("PubMed done")


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
            m, ca = load_df1(conn, filepath, area, categoria_lookup, pais_lookup, posicion_lookup, gender_map, journal_lookup)
            doi_to_paper_id.update(m)
            counter_area_to_doi.update(ca)
        else:
            log.warning(f"DF1 file not found: {filepath}")

    df2_path = "data/raw/df2_norepeated.csv"
    if Path(df2_path).exists():
        load_df2(conn, df2_path, pais_lookup, posicion_lookup, gender_map, doi_to_paper_id, counter_area_to_doi)
    else:
        log.warning(f"DF2 file not found: {df2_path}")

    dblp_path = "data/raw/dblp_authors.csv"
    if Path(dblp_path).exists():
        load_dblp(conn, dblp_path, pais_lookup, categoria_lookup, posicion_lookup, gender_map, journal_lookup)
    else:
        log.warning(f"DBLP file not found: {dblp_path}")

    pubmed_path = "data/raw/pubmed_articles.csv"
    if Path(pubmed_path).exists():
        load_pubmed(conn, pubmed_path, pais_lookup, categoria_lookup, posicion_lookup, gender_map, journal_lookup)
    else:
        log.warning(f"PubMed file not found: {pubmed_path}")

    conn.commit()
    conn.close()
    log.info("All sources loaded. Done.")


if __name__ == "__main__":
    main()
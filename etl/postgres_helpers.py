import logging

import psycopg

from etl.common import truncate

log = logging.getLogger(__name__)


def build_lookups(conn):
    pais_lookup = {}
    with conn.cursor() as cur:
        cur.execute("SELECT \"Id\", \"Nombre\" FROM \"Pais\"")
        for row in cur:
            pais_lookup[row[1].upper()] = row[0]

    categoria_lookup = {}
    with conn.cursor() as cur:
        cur.execute("SELECT \"Id\", \"Nombre\" FROM \"Categoria\"")
        for row in cur:
            categoria_lookup[row[1]] = row[0]

    posicion_lookup = {}
    with conn.cursor() as cur:
        cur.execute("SELECT \"Id\", \"PosicionInteres\" FROM \"Posicion\"")
        for row in cur:
            posicion_lookup[row[1]] = row[0]

    journal_lookup = {}
    with conn.cursor() as cur:
        cur.execute("SELECT \"Id\", \"Nombre\" FROM \"Journal\"")
        for row in cur:
            journal_lookup[row[1].upper()] = row[0]

    log.info(f"Loaded {len(pais_lookup)} pais, {len(categoria_lookup)} categoria, "
            f"{len(posicion_lookup)} posicion, {len(journal_lookup)} journal (existing)")
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
            journal_lookup[key] = row[0]
            return row[0]
        cur.execute("SELECT \"Id\" FROM \"Journal\" WHERE \"Nombre\" = %s", (journal_name.strip(),))
        row = cur.fetchone()
        if row:
            journal_lookup[key] = row[0]
            return row[0]
    return None


def ensure_paper_by_doi(conn, doi, year, id_journal, id_categoria, id_pais):
    if not doi or not doi.strip():
        return None
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO "Paper" ("Año", "Doi", "Id_Journal", "Id_Categoria", "Id_Pais")
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT ("Doi") DO NOTHING
               RETURNING "Id" """,
            (year, doi.strip(), id_journal, id_categoria, id_pais),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("SELECT \"Id\" FROM \"Paper\" WHERE \"Doi\" = %s", (doi.strip(),))
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
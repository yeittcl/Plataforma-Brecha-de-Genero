import json
import logging
import time
import unicodedata
from urllib.parse import quote
from urllib.request import urlopen
from urllib.error import HTTPError

from etl.common import get_postgres_cnx, load_env, truncate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

OPENALEX_API = "https://api.openalex.org"
API_KEY_MASK = "***"
MAX_RETRIES = 5
SLEEP_BETWEEN = 0.01

_api_key = ""
_mailto = ""


def fetch_json(url):
    safe_url = url.replace(_api_key, API_KEY_MASK) if _api_key else url
    for attempt in range(MAX_RETRIES):
        try:
            with urlopen(url, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 429:
                wait = (attempt + 1) * 2
                log.warning(f"Rate limited, sleeping {wait}s...")
                time.sleep(wait)
                continue
            log.error(f"HTTP {e.code} for {safe_url}: {e}")
            return None
        except Exception as e:
            log.error(f"Error fetching {safe_url}: {e}")
            time.sleep(2)
    return None


def search_openalex(query):
    if not query or not query.strip():
        return []
    url = f"{OPENALEX_API}/sources?filter=display_name.search:{quote(query)}&per_page=10"
    if _api_key:
        url += f"&api_key={_api_key}"
    if _mailto:
        url += f"&mailto={_mailto}"
    data = fetch_json(url)
    if not data:
        return []
    return data.get("results", [])


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def find_journal_in_openalex(journal_name):
    name = journal_name.strip()
    if not name:
        return None
    candidates = [name]

    for sep in [" (", " - ", " :"]:
        if sep in name:
            candidates.append(name.split(sep)[0].strip())

    no_parens = name.split("(")[0].strip() if "(" in name else None
    if no_parens and no_parens not in candidates:
        candidates.append(no_parens)

    no_accents = strip_accents(name)
    if no_accents != name and no_accents not in candidates:
        candidates.append(no_accents)
    for c in list(candidates):
        ca = strip_accents(c)
        if ca != c and ca not in candidates:
            candidates.append(ca)

    seen = set()
    for cand in candidates:
        if not cand or cand in seen:
            continue
        seen.add(cand)
        try:
            results = search_openalex(cand)
        except Exception as e:
            log.warning(f"Search error for {cand!r}: {e}")
            continue
        if not results:
            continue
        cand_upper = cand.strip().upper()
        cand_no_acc = strip_accents(cand).strip().upper()
        for r in results:
            rname = r.get("display_name", "").strip().upper()
            if rname == cand_upper:
                return r
        for r in results:
            rname = strip_accents(r.get("display_name", "")).strip().upper()
            if rname == cand_no_acc:
                return r
    return None


def load_journals_no_editorial(conn):
    mapping = {}
    with conn.cursor() as cur:
        cur.execute('SELECT "Id", "Nombre" FROM "Journal" WHERE "Id_Editorial" IS NULL')
        for jid, nombre in cur:
            mapping[nombre.strip()] = jid
    log.info(f"Loaded {len(mapping)} journals without editorial")
    return mapping


def upsert_editorial(conn, nombre, openalex_id):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO "Editorial" ("Nombre", "OpenAlex_Id")
               VALUES (%s, %s)
               ON CONFLICT ("OpenAlex_Id") DO UPDATE
                   SET "Nombre" = COALESCE(EXCLUDED."Nombre", "Editorial"."Nombre")
               RETURNING "Id" """,
            (truncate(nombre, 500), openalex_id),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute('SELECT "Id" FROM "Editorial" WHERE "OpenAlex_Id" = %s', (openalex_id,))
        row = cur.fetchone()
        return row[0] if row else None


def update_journal_editorial(conn, journal_id, editorial_id):
    with conn.cursor() as cur:
        cur.execute(
            'UPDATE "Journal" SET "Id_Editorial" = %s WHERE "Id" = %s AND "Id_Editorial" IS NULL',
            (editorial_id, journal_id),
        )
        return cur.rowcount


def main():
    global _api_key, _mailto
    env = load_env()
    _api_key = env.get("OPENALEX_API_KEY", "")
    _mailto = env.get("OPENALEX_MAILTO", "")
    if _api_key:
        log.info("OpenAlex API key loaded (using higher rate limit)")
    if _mailto:
        log.info(f"OpenAlex mailto: {_mailto}")

    conn = get_postgres_cnx()
    log.info("Connected to Postgres")

    journals_no_ed = load_journals_no_editorial(conn)
    if not journals_no_ed:
        log.info("All journals already have editorial. Nothing to do.")
        conn.close()
        return

    total = len(journals_no_ed)
    matched = 0
    unmatched = 0
    no_publisher = 0

    for i, (journal_name, journal_id) in enumerate(journals_no_ed.items(), 1):
        source = find_journal_in_openalex(journal_name)
        if not source:
            unmatched += 1
            continue

        pub = source.get("host_organization_name") or source.get("publisher")
        if isinstance(pub, dict):
            pub_name = pub.get("display_name")
            pub_id = pub.get("id")
        elif isinstance(pub, str):
            pub_name = pub
            pub_id = None
        else:
            no_publisher += 1
            continue

        if not pub_name:
            no_publisher += 1
            continue

        if pub_id:
            pub_id_str = pub_id.split("/")[-1] if "/" in pub_id else pub_id
        else:
            pub_id_str = None

        eid = upsert_editorial(conn, pub_name, pub_id_str) if pub_id_str else None
        if not eid:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO "Editorial" ("Nombre") VALUES (%s)
                   ON CONFLICT ("Nombre") DO NOTHING RETURNING "Id" """,
                (truncate(pub_name, 500),),
            )
            row = cur.fetchone()
            if row:
                eid = row[0]
            else:
                cur.execute('SELECT "Id" FROM "Editorial" WHERE "Nombre" = %s', (pub_name,))
                row = cur.fetchone()
                eid = row[0] if row else None

        if not eid:
            no_publisher += 1
            continue

        if update_journal_editorial(conn, journal_id, eid):
            matched += 1

        if i % 50 == 0:
            conn.commit()
            log.info(f"Progress: {i}/{total}, matched={matched}, unmatched={unmatched}, no_publisher={no_publisher}")

        time.sleep(SLEEP_BETWEEN)

    conn.commit()
    conn.close()
    log.info(f"Done. Total: {total}, Matched: {matched}, Unmatched: {unmatched}, No publisher: {no_publisher}")


if __name__ == "__main__":
    main()
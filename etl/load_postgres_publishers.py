import json
import logging
import time
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError

from etl.common import get_postgres_cnx, load_env, truncate
from etl.postgres_helpers import build_lookups

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

OPENALEX_API = "https://api.openalex.org"
CACHE_DIR = Path("data/cache")
CURSOR_FILE = CACHE_DIR / "openalex_publishers_cursor.txt"
PER_PAGE = 100
SLEEP_BETWEEN = 0.12
MAX_RETRIES = 5


def fetch_json(url):
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
            log.error(f"HTTP {e.code} for {url}: {e}")
            return None
        except Exception as e:
            log.error(f"Error fetching {url}: {e}")
            time.sleep(2)
    return None


def load_cursor():
    if CURSOR_FILE.exists():
        return CURSOR_FILE.read_text().strip() or None
    return None


def save_cursor(cursor):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CURSOR_FILE.write_text(cursor or "")


def load_journals_no_editorial(conn):
    mapping = {}
    with conn.cursor() as cur:
        cur.execute("SELECT \"Id\", \"Nombre\" FROM \"Journal\" WHERE \"Id_Editorial\" IS NULL")
        for jid, nombre in cur:
            mapping[nombre.strip().upper()] = jid
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
        cur.execute("SELECT \"Id\" FROM \"Editorial\" WHERE \"OpenAlex_Id\" = %s", (openalex_id,))
        row = cur.fetchone()
        return row[0] if row else None


def update_journal_editorial(conn, journal_id, editorial_id):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE \"Journal\" SET \"Id_Editorial\" = %s WHERE \"Id\" = %s AND \"Id_Editorial\" IS NULL",
            (editorial_id, journal_id),
        )
        return cur.rowcount


def main():
    load_env()
    conn = get_postgres_cnx()
    log.info("Connected to Postgres")

    journals_no_ed = load_journals_no_editorial(conn)
    if not journals_no_ed:
        log.info("All journals already have editorial. Nothing to do.")
        conn.close()
        return

    cursor = load_cursor()
    url = f"{OPENALEX_API}/sources?per_page={PER_PAGE}"
    if cursor:
        url += f"&cursor={cursor}"
        log.info(f"Resuming from cursor: {cursor[:20]}...")
    else:
        log.info("Starting fresh pagination of OpenAlex /sources")

    editorial_cache = {}
    sources_seen = 0
    pages_seen = 0
    journals_updated = 0
    publishers_created = 0
    remaining = dict(journals_no_ed)

    while remaining:
        data = fetch_json(url)
        if not data:
            log.error("Failed to fetch page, aborting")
            break

        results = data.get("results", [])
        pages_seen += 1

        for source in results:
            sources_seen += 1
            pub = source.get("host_organization_name") or source.get("publisher")
            if isinstance(pub, dict):
                publisher_name = pub.get("display_name")
                publisher_id = pub.get("id")
            else:
                publisher_name = source.get("host_organization_name")
                publisher_id = None

            if not publisher_name or not publisher_id:
                continue

            publisher_id_str = publisher_id.split("/")[-1] if "/" in publisher_id else publisher_id

            if publisher_id_str in editorial_cache:
                eid = editorial_cache[publisher_id_str]
            else:
                eid = upsert_editorial(conn, publisher_name, publisher_id_str)
                if eid:
                    editorial_cache[publisher_id_str] = eid
                    publishers_created += 1

            if not eid:
                continue

            source_name = source.get("display_name", "")
            key = source_name.strip().upper()
            jid = remaining.get(key)
            if jid:
                rc = update_journal_editorial(conn, jid, eid)
                if rc:
                    journals_updated += 1
                    del remaining[key]

        conn.commit()
        log.info(f"Page {pages_seen}: {sources_seen} sources, {journals_updated} journals updated, {len(remaining)} remaining")

        if not remaining:
            log.info("All journals matched!")
            save_cursor(None)
            break

        meta = data.get("meta", {})
        next_cursor = meta.get("next_cursor")
        if not next_cursor:
            log.info(f"Reached end of OpenAlex /sources. {len(remaining)} journals unmatched.")
            save_cursor(None)
            break

        url = f"{OPENALEX_API}/sources?per_page={PER_PAGE}&cursor={next_cursor}"
        save_cursor(next_cursor)
        time.sleep(SLEEP_BETWEEN)

    conn.close()
    log.info(f"Done. {pages_seen} pages, {sources_seen} sources, {publishers_created} publishers, "
             f"{journals_updated} journals updated, {len(remaining)} unmatched")


if __name__ == "__main__":
    main()
import json
import logging
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen
from urllib.error import HTTPError

from etl.common import get_postgres_cnx, load_env, truncate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

OPENALEX_API = "https://api.openalex.org"
API_KEY_MASK = "***"
CACHE_DIR = Path("data/cache")
CACHE_FILE = CACHE_DIR / "publishers_search_cache.json"
MAX_RETRIES = 8
SLEEP_BETWEEN = 0.02
CREDIT_WARN_THRESHOLD = 8000
CREDIT_HARD_LIMIT = 9500

_api_key = ""
_mailto = ""
_request_count = 0


def _increment_request_count():
    global _request_count
    _request_count += 1
    if _request_count == CREDIT_WARN_THRESHOLD:
        log.warning(f"Approaching OpenAlex daily credit budget (~{CREDIT_WARN_THRESHOLD} requests)")
    if _request_count >= CREDIT_HARD_LIMIT:
        log.error(f"Hit hard credit limit ({CREDIT_HARD_LIMIT} requests). Stopping to preserve budget.")
        raise CreditLimitExceeded()


class CreditLimitExceeded(Exception):
    pass


def fetch_json(url):
    safe_url = url.replace(_api_key, API_KEY_MASK) if _api_key else url
    for attempt in range(MAX_RETRIES):
        try:
            with urlopen(url, timeout=30) as resp:
                _increment_request_count()
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 429:
                retry_after = e.headers.get("Retry-After") if hasattr(e, "headers") else None
                if retry_after:
                    try:
                        wait = int(retry_after)
                    except (ValueError, TypeError):
                        wait = min(2 ** attempt, 60)
                else:
                    wait = min(2 ** attempt, 60)
                log.warning(f"Rate limited, sleeping {wait}s (attempt {attempt+1}/{MAX_RETRIES})...")
                time.sleep(wait)
                continue
            log.error(f"HTTP {e.code} for {safe_url}: {e}")
            return None
        except Exception as e:
            log.error(f"Error fetching {safe_url}: {e}")
            time.sleep(2)
    log.error(f"Max retries ({MAX_RETRIES}) exhausted for {safe_url}")
    return None


def load_search_cache():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"Cache file corrupted, starting fresh: {e}")
    return {}


def save_search_cache(cache):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


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


def find_journal_in_openalex(journal_name, cache):
    if journal_name in cache:
        return cache[journal_name]

    name = journal_name.strip()
    if not name:
        cache[journal_name] = None
        return None

    primary_results = search_openalex(name)
    cand_upper = name.upper()
    for r in primary_results:
        rname = r.get("display_name", "").strip().upper()
        if rname == cand_upper:
            cache[journal_name] = r
            return r

    if not primary_results:
        no_accents = strip_accents(name)
        if no_accents != name:
            fallback_results = search_openalex(no_accents)
            cand_no_acc_upper = no_accents.upper()
            for r in fallback_results:
                rname = strip_accents(r.get("display_name", "")).strip().upper()
                if rname == cand_no_acc_upper:
                    cache[journal_name] = r
                    return r

    cache[journal_name] = None
    return None


def load_journals_no_editorial(conn):
    mapping = {}
    with conn.cursor() as cur:
        cur.execute('SELECT "Id", "Nombre" FROM "Journal" WHERE "Id_Editorial" IS NULL')
        for jid, nombre in cur:
            mapping[nombre.strip()] = jid
    log.info(f"Loaded {len(mapping)} journals without editorial")
    return mapping


def upsert_editorial(conn, nombre, openalex_id=None):
    if openalex_id:
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
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO "Editorial" ("Nombre")
               VALUES (%s)
               ON CONFLICT ("Nombre") DO UPDATE
                   SET "Nombre" = EXCLUDED."Nombre"
               RETURNING "Id" """,
            (truncate(nombre, 500),),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute('SELECT "Id" FROM "Editorial" WHERE "Nombre" = %s', (nombre,))
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
    global _api_key, _mailto, _request_count
    env = load_env()
    _api_key = env.get("OPENALEX_API_KEY", "")
    _mailto = env.get("OPENALEX_MAILTO", "")
    if _api_key:
        log.info("OpenAlex API key loaded (using higher rate limit)")
    if _mailto:
        log.info(f"OpenAlex mailto: {_mailto}")

    cache = load_search_cache()
    if cache:
        log.info(f"Loaded search cache: {len(cache)} entries")

    conn = get_postgres_cnx()
    log.info("Connected to Postgres")

    journals_no_ed = load_journals_no_editorial(conn)
    if not journals_no_ed:
        log.info("All journals already have editorial. Nothing to do.")
        conn.close()
        return

    total = len(journals_no_ed)
    cache_hits = sum(1 for jn in journals_no_ed if jn in cache)
    log.info(f"Cache hits before any API call: {cache_hits}/{total}")

    matched = 0
    unmatched = 0
    no_publisher = 0
    cache_writes = 0

    try:
        for i, (journal_name, journal_id) in enumerate(journals_no_ed.items(), 1):
            if journal_name in cache and cache[journal_name] is None:
                unmatched += 1
                continue
            if journal_name in cache and cache[journal_name] is not None:
                source = cache[journal_name]
            else:
                source = find_journal_in_openalex(journal_name, cache)
                cache_writes += 1
                if cache_writes % 100 == 0:
                    save_search_cache(cache)

            if not source:
                unmatched += 1
                continue

            pub = source.get("host_organization_name")
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

            pub_id_str = None
            if pub_id:
                pub_id_str = pub_id.split("/")[-1] if "/" in pub_id else pub_id

            eid = upsert_editorial(conn, pub_name, pub_id_str)
            if not eid:
                no_publisher += 1
                continue

            if update_journal_editorial(conn, journal_id, eid):
                matched += 1

            if i % 50 == 0:
                conn.commit()
                log.info(f"Progress: {i}/{total}, matched={matched}, unmatched={unmatched}, "
                         f"no_publisher={no_publisher}, requests={_request_count}, "
                         f"cache={len(cache)}")

            time.sleep(SLEEP_BETWEEN)

    except CreditLimitExceeded:
        log.error("Aborting due to credit limit. Cache has been saved.")
    finally:
        save_search_cache(cache)
        conn.commit()
        conn.close()

    log.info(f"Done. Total: {total}, Matched: {matched}, Unmatched: {unmatched}, "
             f"No publisher: {no_publisher}, API requests used: {_request_count}, "
             f"Cache entries: {len(cache)}")


if __name__ == "__main__":
    main()
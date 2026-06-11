import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

import clickhouse_connect
import psycopg

def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
    required = [
        "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB",
        "POSTGRES_USER", "POSTGRES_PASSWORD",
        "CLICKHOUSE_HOST", "CLICKHOUSE_HTTP_PORT",
        "CLICKHOUSE_DB", "CLICKHOUSE_USER", "CLICKHOUSE_PASSWORD",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")
    env = {k: os.getenv(k) for k in required}
    env["OPENALEX_API_KEY"] = os.getenv("OPENALEX_API_KEY", "")
    env["OPENALEX_MAILTO"] = os.getenv("OPENALEX_MAILTO", "")
    return env


def get_postgres_cnx():
    env = load_env()
    conn = psycopg.connect(
        host=env["POSTGRES_HOST"],
        port=int(env["POSTGRES_PORT"]),
        dbname=env["POSTGRES_DB"],
        user=env["POSTGRES_USER"],
        password=env["POSTGRES_PASSWORD"],
        autocommit=False,
    )
    return conn


def get_clickhouse_cnx():
    env = load_env()
    client = clickhouse_connect.get_client(
        host=env["CLICKHOUSE_HOST"],
        port=int(env["CLICKHOUSE_HTTP_PORT"]),
        database=env["CLICKHOUSE_DB"],
        username=env["CLICKHOUSE_USER"],
        password=env["CLICKHOUSE_PASSWORD"],
    )
    return client


_POSITION_MAP = {
    "fist": "first",
    "first": "first",
    "second": "second",
    "penultimate": "penultimate",
    "last": "last",
}


def normalize_position(raw: str) -> str:
    if not raw:
        return "other"
    return _POSITION_MAP.get(raw.strip().lower(), "other")


COUNTRY_ALIASES = {
    "UK": "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND",
    "U.K.": "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND",
    "U.K": "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND",
    "UNITED KINGDOM": "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND",
    "GREAT BRITAIN": "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND",
    "BRITAIN": "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND",
    "ENGLAND": "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND",
    "SCOTLAND": "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND",
    "WALES": "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND",
    "USA": "UNITED STATES",
    "U.S.A.": "UNITED STATES",
    "U.S.A": "UNITED STATES",
    "US": "UNITED STATES",
    "U.S.": "UNITED STATES",
    "U.S": "UNITED STATES",
    "AMERICA": "UNITED STATES",
    "UAE": "UNITED ARAB EMIRATES",
    "U.A.E.": "UNITED ARAB EMIRATES",
    "U.A.E": "UNITED ARAB EMIRATES",
    "CZECH REPUBLIC": "CZECHIA",
    "CZECH REP.": "CZECHIA",
    "RUSSIA": "RUSSIAN FEDERATION",
    "SOUTH KOREA": "KOREA SOUTH",
    "NORTH KOREA": "NORTH KOREA",
    "S. KOREA": "KOREA SOUTH",
    "PRK": "NORTH KOREA",
    "DPRK": "NORTH KOREA",
    "IRAN": "IRAN (ISLAMIC REPUBLIC OF)",
    "SYRIA": "SYRIAN ARAB REPUBLIC",
    "VENEZUELA": "VENEZUELA (BOLIVARIAN REPUBLIC OF)",
    "BOLIVIA": "BOLIVIA (PLURINATIONAL STATE OF)",
    "TANZANIA": "TANZANIA, UNITED REPUBLIC OF",
    "MOLDOVA": "MOLDOVA (REPUBLIC OF)",
    "LAOS": "LAO PEOPLE'S DEMOCRATIC REPUBLIC",
    "PALESTINE": "PALESTINE, STATE OF",
    "VIETNAM": "VIET NAM",
    "CAPE VERDE": "CABO VERDE",
    "CONGO": "CONGO, DEMOCRATIC REPUBLIC OF THE",
    "DEMOCRATIC REPUBLIC OF THE CONGO": "CONGO, DEMOCRATIC REPUBLIC OF THE",
    "DEMOCRATIC REPUBLIC OF CONGO": "CONGO, DEMOCRATIC REPUBLIC OF THE",
    "TIMOR LESTE": "TIMOR-LESTE",
    "THE BAHAMAS": "BAHAMAS",
}


def normalize_country(raw: str) -> str:
    if not raw:
        return "Unknown"
    normalized = " ".join(raw.strip().upper().split())
    if normalized in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[normalized]
    return normalized if normalized else "Unknown"


def normalize_firstname(raw: str) -> str:
    if not raw:
        return "Unknown"
    normalized = raw.strip().title()
    return normalized if normalized else "Unknown"


def truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len]


def progress_bar(iterable, desc: str = "", total: int = None):
    return tqdm(iterable, desc=desc, total=total)
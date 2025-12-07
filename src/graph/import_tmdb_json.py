import argparse
import json
import logging
import os
from typing import Any, Dict, Iterable, List, Optional

import psycopg2
import psycopg2.extras
from urllib.parse import urlparse

from dotenv import load_dotenv
load_dotenv()


DEFAULT_DB_CONFIG = {
    "dbname": os.getenv("PGDATABASE", "postgres"),
    "user": os.getenv("PGUSER", "postgres"),
    "password": os.getenv("PGPASSWORD", "password"),
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "6543")),
}


def configure_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def load_json(path: str) -> List[Dict[str, Any]]:
    logging.info("Loading JSON from %s", path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logging.error("JSON file not found: %s", path)
        raise
    except json.JSONDecodeError as e:
        logging.error("Invalid JSON: %s", e)
        raise

    if not isinstance(data, list):
        raise ValueError("Top-level JSON must be a list of records")
    logging.info("Loaded %d records", len(data))
    return data


def coerce_int(value: Optional[Any]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        logging.debug("Failed to convert %r to int", value)
        return None


def transform_record(r: Dict[str, Any]) -> Dict[str, Any]:
    tmdb_id = r.get("tmdb_id")
    if tmdb_id is None:
        raise ValueError("Record missing required field 'tmdb_id'")

    year = coerce_int(r.get("nam_phat_hanh"))

    def as_jsonb(value: Any) -> Optional[psycopg2.extras.Json]:
        if value is None:
            return None
        return psycopg2.extras.Json(value)

    transformed = {
        "tmdb_id": tmdb_id,
        "ten_phim_tv": r.get("ten_phim_tv"),
        "ten_phim_ta": r.get("ten_phim_ta"),
        "dao_dien": r.get("dao_dien"),
        "nhan_vat_chinh": as_jsonb(r.get("nhan_vat_chinh")),
        "the_loai": as_jsonb(r.get("the_loai")),
        "nam_phat_hanh": year,
        "mo_ta": r.get("mo_ta"),
        "diem_danh_gia": r.get("diem_danh_gia"),
        "series_info": as_jsonb(r.get("series_info")),
    }
    return transformed

def connect_db(db_config: Dict[str, Any]):
    dsn = db_config.get("database_url")
    if dsn:
        logging.info("Connecting via DATABASE_URL")
        # Append sslmode=require if not present
        if "sslmode=" not in dsn:
            connector = "?" if "?" not in dsn else "&"
            dsn = f"{dsn}{connector}sslmode={db_config.get('sslmode', 'require')}"
        return psycopg2.connect(dsn)

    # Fallback to discrete params
    host = db_config.get("host")
    dbname = db_config.get("dbname")
    logging.info("Connecting to PostgreSQL: host=%s dbname=%s", host, dbname)
    params = dict(db_config)
    # If remote host, default to sslmode=require
    if host and host not in ("localhost", "127.0.0.1"):
        params.setdefault("sslmode", db_config.get("sslmode", "require"))
    # Remove helper keys
    params.pop("database_url", None)
    return psycopg2.connect(**params)


def create_table_if_not_exists(conn) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS tmdb_movies (
        tmdb_id BIGINT PRIMARY KEY,
        ten_phim_tv TEXT,
        ten_phim_ta TEXT,
        dao_dien TEXT,
        nhan_vat_chinh JSONB,
        the_loai JSONB,
        nam_phat_hanh INT,
        mo_ta TEXT,
        diem_danh_gia FLOAT,
        series_info JSONB
    );
    """
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    logging.info("Ensured table 'tmdb_movies' exists")


def upsert_records(conn, records: Iterable[Dict[str, Any]], batch_size: int = 1000) -> int:
    columns = [
        "tmdb_id",
        "ten_phim_tv",
        "ten_phim_ta",
        "dao_dien",
        "nhan_vat_chinh",
        "the_loai",
        "nam_phat_hanh",
        "mo_ta",
        "diem_danh_gia",
        "series_info",
    ]

    insert_sql = f"""
        INSERT INTO tmdb_movies ({", ".join(columns)})
        VALUES %s
        ON CONFLICT (tmdb_id) DO UPDATE SET
            ten_phim_tv = EXCLUDED.ten_phim_tv,
            ten_phim_ta = EXCLUDED.ten_phim_ta,
            dao_dien = EXCLUDED.dao_dien,
            nhan_vat_chinh = EXCLUDED.nhan_vat_chinh,
            the_loai = EXCLUDED.the_loai,
            nam_phat_hanh = EXCLUDED.nam_phat_hanh,
            mo_ta = EXCLUDED.mo_ta,
            diem_danh_gia = EXCLUDED.diem_danh_gia,
            series_info = EXCLUDED.series_info
    """

    total = 0
    with conn.cursor() as cur:
        batch: List[List[Any]] = []
        for r in records:
            tr = transform_record(r)
            row = [tr[c] for c in columns]
            batch.append(row)
            if len(batch) >= batch_size:
                psycopg2.extras.execute_values(cur, insert_sql, batch, page_size=batch_size)
                total += len(batch)
                logging.debug("Upserted batch of %d records", len(batch))
                batch = []

        if batch:
            psycopg2.extras.execute_values(cur, insert_sql, batch, page_size=batch_size)
            total += len(batch)
            logging.debug("Upserted final batch of %d records", len(batch))

    conn.commit()
    logging.info("Upserted %d records", total)
    return total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import TMDB JSON into PostgreSQL")
    parser.add_argument(
        "--json-path",
        default=os.path.join(os.path.dirname(__file__), "../data/tmdb_movies_final.json"),
        help="Path to tmdb_movies_final.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate JSON only; do not connect to DB",
    )
    parser.add_argument("--dbname", default=DEFAULT_DB_CONFIG["dbname"], help="PostgreSQL database name")
    parser.add_argument("--user", default=DEFAULT_DB_CONFIG["user"], help="PostgreSQL user")
    parser.add_argument("--password", default=DEFAULT_DB_CONFIG["password"], help="PostgreSQL password")
    parser.add_argument("--host", default=DEFAULT_DB_CONFIG["host"], help="PostgreSQL host")
    parser.add_argument("--port", type=int, default=DEFAULT_DB_CONFIG["port"], help="PostgreSQL port")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL"), help="PostgreSQL connection URL")
    parser.add_argument("--sslmode", default=os.getenv("PGSSLMODE", None), help="PostgreSQL sslmode")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase log verbosity")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(args.verbose)

    db_config = {
        "dbname": args.dbname,
        "user": args.user,
        "password": args.password,
        "host": args.host,
        "port": args.port,
        "database_url": args.database_url,
        "sslmode": args.sslmode,
    }

    try:
        data = load_json(args.json_path)
    except Exception:
        logging.exception("Failed to load JSON data")
        raise

    if args.dry_run:
        logging.info("Dry-run enabled: JSON parsed and validated. Skipping DB operations.")
        return

    try:
        with connect_db(db_config) as conn:
            create_table_if_not_exists(conn)
            upsert_records(conn, data)
    except psycopg2.OperationalError as e:
        logging.error("Database connection failed: %s", e)
        raise
    except Exception:
        logging.exception("Database operation failed")
        raise

    logging.info("Import completed successfully")


if __name__ == "__main__":
    main()

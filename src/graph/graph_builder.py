import argparse
import logging
import os
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple

import psycopg2
import psycopg2.extras
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
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def connect_db(db_config: Dict[str, Any]):
    dsn = db_config.get("database_url")
    if dsn:
        logging.info("Connecting via DATABASE_URL")
        if "sslmode=" not in dsn:
            connector = "?" if "?" not in dsn else "&"
            dsn = f"{dsn}{connector}sslmode={db_config.get('sslmode', 'require')}"
        return psycopg2.connect(dsn)

    host = db_config.get("host")
    dbname = db_config.get("dbname")
    logging.info("Connecting to PostgreSQL: host=%s dbname=%s", host, dbname)
    params = dict(db_config)
    if host and host not in ("localhost", "127.0.0.1"):
        params.setdefault("sslmode", db_config.get("sslmode", "require"))
    params.pop("database_url", None)
    return psycopg2.connect(**params)


def create_graph_tables(conn) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS movies_graph (
        movie_id BIGINT PRIMARY KEY,
        title TEXT,
        year INT,
        description TEXT,
        score FLOAT
    );

    CREATE TABLE IF NOT EXISTS people_graph (
        person_id UUID PRIMARY KEY,
        name TEXT UNIQUE
    );

    CREATE TABLE IF NOT EXISTS genres_graph (
        genre_id UUID PRIMARY KEY,
        name TEXT UNIQUE
    );

    CREATE TABLE IF NOT EXISTS movie_person_relationship (
        movie_id BIGINT,
        person_id UUID,
        rel_type TEXT,
        UNIQUE (movie_id, person_id, rel_type)
    );

    CREATE TABLE IF NOT EXISTS movie_genre_relationship (
        movie_id BIGINT,
        genre_id UUID,
        UNIQUE (movie_id, genre_id)
    );

    CREATE TABLE IF NOT EXISTS person_person_relationship (
        person_id_1 UUID,
        person_id_2 UUID,
        rel_type TEXT,
        UNIQUE (person_id_1, person_id_2, rel_type)
    );

    CREATE TABLE IF NOT EXISTS person_genre_relationship (
        person_id UUID,
        genre_id UUID,
        rel_type TEXT,
        UNIQUE (person_id, genre_id, rel_type)
    );
    """
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    logging.info("Ensured graph tables exist")


def fetch_tmdb_movies(conn) -> List[Dict[str, Any]]:
    query = """
        SELECT tmdb_id, ten_phim_tv, ten_phim_ta, dao_dien,
               nhan_vat_chinh, the_loai, nam_phat_hanh,
               mo_ta, diem_danh_gia
        FROM tmdb_movies
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query)
        rows = cur.fetchall()
    logging.info("Fetched %d tmdb_movies rows", len(rows))
    return rows


def coerce_year(value: Optional[Any]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        logging.debug("Invalid year value: %r", value)
        return None


def normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    s = value.strip()
    return s if s else None


def get_movie_title(row: Dict[str, Any]) -> Optional[str]:
    # prefer local-language title then English
    return normalize_text(row.get("ten_phim_tv")) or normalize_text(row.get("ten_phim_ta"))


def ensure_person(name: str, people_cache: Dict[str, uuid.UUID], created_people: Optional[set] = None) -> Tuple[uuid.UUID, str, bool]:
    key = name.strip()
    if key in people_cache:
        return people_cache[key], key, False
    pid = uuid.uuid4()
    people_cache[key] = pid
    if created_people is not None:
        created_people.add(key)
    return pid, key, True


def ensure_genre(name: str, genres_cache: Dict[str, uuid.UUID], created_genres: Optional[set] = None) -> Tuple[uuid.UUID, str, bool]:
    key = name.strip()
    if key in genres_cache:
        return genres_cache[key], key, False
    gid = uuid.uuid4()
    genres_cache[key] = gid
    if created_genres is not None:
        created_genres.add(key)
    return gid, key, True


def preload_caches(conn) -> Tuple[Dict[str, uuid.UUID], Dict[str, uuid.UUID]]:
    people_cache: Dict[str, uuid.UUID] = {}
    genres_cache: Dict[str, uuid.UUID] = {}
    with conn.cursor() as cur:
        cur.execute("SELECT person_id, name FROM people_graph")
        for pid, name in cur.fetchall():
            if name:
                people_cache[name.strip()] = pid
        cur.execute("SELECT genre_id, name FROM genres_graph")
        for gid, name in cur.fetchall():
            if name:
                genres_cache[name.strip()] = gid
    logging.info("Preloaded %d people and %d genres", len(people_cache), len(genres_cache))
    return people_cache, genres_cache


def upsert_graph(conn, movies: List[Dict[str, Any]]) -> None:
    people_cache, genres_cache = preload_caches(conn)

    # Prepare batches
    movie_rows: List[List[Any]] = []
    person_rows: List[List[Any]] = []
    genre_rows: List[List[Any]] = []
    mp_rel_rows: List[List[Any]] = []
    mg_rel_rows: List[List[Any]] = []
    pp_rel_rows: List[List[Any]] = []
    pg_rel_rows: List[List[Any]] = []

    created_people_names: set = set()
    created_genre_names: set = set()

    # To avoid duplicate person-person edges in batch
    pp_seen: set = set()

    for row in movies:
        movie_id = row.get("tmdb_id")
        title = get_movie_title(row)
        year = coerce_year(row.get("nam_phat_hanh"))
        description = row.get("mo_ta")
        score = row.get("diem_danh_gia")
        movie_rows.append([movie_id, title, year, description, score])

        # Director(s)
        director = row.get("dao_dien")
        director_id: Optional[uuid.UUID] = None
        if director:
            pid, pname, is_new = ensure_person(director, people_cache, created_people_names)
            director_id = pid
            if is_new:
                person_rows.append([pid, pname])
            mp_rel_rows.append([movie_id, pid, "DIRECTOR"])

        # Actors list 
        actors = row.get("nhan_vat_chinh")
        actor_ids: List[uuid.UUID] = []
        if isinstance(actors, list):
            for a in actors:
                if not a:
                    continue
                pid, pname, is_new = ensure_person(str(a), people_cache, created_people_names)
                if is_new:
                    person_rows.append([pid, pname])
                actor_ids.append(pid)
                mp_rel_rows.append([movie_id, pid, "ACTOR"])

        # Genres list 
        genres = row.get("the_loai")
        genre_ids: List[uuid.UUID] = []
        if isinstance(genres, list):
            for g in genres:
                if not g:
                    continue
                gid, gname, is_new = ensure_genre(str(g), genres_cache, created_genre_names)
                if is_new:
                    genre_rows.append([gid, gname])
                genre_ids.append(gid)
                mg_rel_rows.append([movie_id, gid])

        # Additional relationships to boost graph connectivity
        # 1) CO_ACTED_WITH among actors (undirected -> store ordered pair)
        n = len(actor_ids)
        for i in range(n):
            for j in range(i + 1, n):
                a1, a2 = actor_ids[i], actor_ids[j]
                key = (str(min(a1, a2)), str(max(a1, a2)), "CO_ACTED_WITH")
                if key not in pp_seen:
                    pp_seen.add(key)
                    pp_rel_rows.append([key[0], key[1], key[2]])

        # 2) WORKED_WITH between director and each actor
        if director_id is not None:
            for aid in actor_ids:
                p1, p2 = (str(min(director_id, aid)), str(max(director_id, aid)))
                key = (p1, p2, "WORKED_WITH")
                if key not in pp_seen:
                    pp_seen.add(key)
                    pp_rel_rows.append([p1, p2, "WORKED_WITH"])

        # 3) Person-Genre relationships (ACTS_IN_GENRE / DIRECTS_GENRE)
        for aid in actor_ids:
            for gid in genre_ids:
                pg_rel_rows.append([str(aid), str(gid), "ACTS_IN_GENRE"])
        if director_id is not None:
            for gid in genre_ids:
                pg_rel_rows.append([str(director_id), str(gid), "DIRECTS_GENRE"])

    with conn.cursor() as cur:
        # movies_graph: upsert by PK
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO movies_graph (movie_id, title, year, description, score)
            VALUES %s
            ON CONFLICT (movie_id) DO UPDATE SET
                title = EXCLUDED.title,
                year = EXCLUDED.year,
                description = EXCLUDED.description,
                score = EXCLUDED.score
            """,
            movie_rows,
            page_size=1000,
        )

        # people_graph: DO NOTHING on conflict(name) via unique constraint
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO people_graph (person_id, name)
            VALUES %s
            ON CONFLICT (name) DO NOTHING
            """,
            person_rows,
            page_size=1000,
        )

        # genres_graph: DO NOTHING on conflict(name)
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO genres_graph (genre_id, name)
            VALUES %s
            ON CONFLICT (name) DO NOTHING
            """,
            genre_rows,
            page_size=1000,
        )

        # movie_person_relationship: unique(movie_id, person_id, rel_type)
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO movie_person_relationship (movie_id, person_id, rel_type)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            mp_rel_rows,
            page_size=1000,
        )

        # movie_genre_relationship: unique(movie_id, genre_id)
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO movie_genre_relationship (movie_id, genre_id)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            mg_rel_rows,
            page_size=1000,
        )

        # person_person_relationship
        if pp_rel_rows:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO person_person_relationship (person_id_1, person_id_2, rel_type)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                pp_rel_rows,
                page_size=1000,
            )

        # person_genre_relationship
        if pg_rel_rows:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO person_genre_relationship (person_id, genre_id, rel_type)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                pg_rel_rows,
                page_size=1000,
            )

    conn.commit()
    logging.info(
        "Upserted: movies=%d people(new)=%d genres(new)=%d rel_person=%d rel_genre=%d co/worked=%d person_genre=%d",
        len(movie_rows), len(created_people_names), len(created_genre_names), len(mp_rel_rows), len(mg_rel_rows), len(pp_rel_rows), len(pg_rel_rows)
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build graph tables from tmdb_movies")
    p.add_argument("--database-url", default=os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL"), help="PostgreSQL connection URL")
    p.add_argument("--sslmode", default=os.getenv("PGSSLMODE", None), help="PostgreSQL sslmode")
    p.add_argument("--host", default=DEFAULT_DB_CONFIG["host"], help="PostgreSQL host")
    p.add_argument("--port", type=int, default=DEFAULT_DB_CONFIG["port"], help="PostgreSQL port")
    p.add_argument("--dbname", default=DEFAULT_DB_CONFIG["dbname"], help="PostgreSQL database name")
    p.add_argument("--user", default=DEFAULT_DB_CONFIG["user"], help="PostgreSQL user")
    p.add_argument("--password", default=DEFAULT_DB_CONFIG["password"], help="PostgreSQL password")
    p.add_argument("-v", "--verbose", action="count", default=0, help="Increase log verbosity")
    return p.parse_args()


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
        with connect_db(db_config) as conn:
            psycopg2.extras.register_uuid(conn_or_curs=conn)
            create_graph_tables(conn)
            movies = fetch_tmdb_movies(conn)
            if not movies:
                logging.warning("No movies found in tmdb_movies")
                return
            upsert_graph(conn, movies)
    except psycopg2.OperationalError as e:
        logging.error("Database connection failed: %s", e)
        logging.error("Provide Supabase DATABASE_URL or SUPABASE_DB_URL or discrete connection params. Supabase typically requires sslmode=require.")
        raise
    except Exception:
        logging.exception("Graph build failed")
        raise

    logging.info("Graph build completed successfully")


if __name__ == "__main__":
    main()

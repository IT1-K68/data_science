import argparse
import logging
import os
from typing import Any, Dict, Iterable, List, Tuple

import psycopg2
import psycopg2.extras
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_CONFIG = {
    "dbname": os.getenv("PGDATABASE", "postgres"),
    "user": os.getenv("PGUSER", "postgres"),
    "password": os.getenv("PGPASSWORD", "password"),
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "6543")),
}

DEFAULT_NEO4J = {
    "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    "user": os.getenv("NEO4J_USERNAME", "neo4j"),
    "password": os.getenv("NEO4J_PASSWORD", "password"),
}


def configure_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def connect_db(cfg: Dict[str, Any]):
    dsn = cfg.get("database_url")
    if dsn:
        logging.info("Connecting via DATABASE_URL")
        if "sslmode=" not in dsn:
            connector = "?" if "?" not in dsn else "&"
            dsn = f"{dsn}{connector}sslmode={cfg.get('sslmode', 'require')}"
        return psycopg2.connect(dsn)
    host = cfg.get("host")
    dbname = cfg.get("dbname")
    logging.info("Connecting to PostgreSQL: host=%s dbname=%s", host, dbname)
    params = dict(cfg)
    if host and host not in ("localhost", "127.0.0.1"):
        params.setdefault("sslmode", cfg.get("sslmode", "require"))
    params.pop("database_url", None)
    return psycopg2.connect(**params)


def connect_neo4j(uri: str, user: str, password: str):
    logging.info("Connecting to Neo4j uri=%s user=%s", uri, user)
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        session.execute_read(lambda tx: tx.run("RETURN 1").consume())
    return driver


def fetch_graph_batches(conn, batch_size: int = 1000) -> Iterable[Dict[str, List[Dict[str, Any]]]]:
    """Yield batches of movies with their people and genres relationships.

    For efficiency, we stream IDs then join in Python per batch.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT movie_id, title, year, description, score FROM movies_graph ORDER BY movie_id")
        movies = cur.fetchall()

    # Build maps for relationships and nodes
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT person_id, name FROM people_graph")
        people = {str(r["person_id"]): r for r in cur.fetchall()}

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT genre_id, name FROM genres_graph")
        genres = {str(r["genre_id"]): r for r in cur.fetchall()}

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT movie_id, person_id, rel_type FROM movie_person_relationship")
        mp = cur.fetchall()

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT movie_id, genre_id FROM movie_genre_relationship")
        mg = cur.fetchall()

    # Index relationships by movie
    by_movie_people: Dict[int, List[Dict[str, Any]]] = {}
    for r in mp:
        mid = r["movie_id"]
        pid = str(r["person_id"]) 
        rel = r["rel_type"]
        person = people.get(pid)
        if not person:
            continue
        by_movie_people.setdefault(mid, []).append({"person_id": pid, "name": person["name"], "rel_type": rel})

    by_movie_genres: Dict[int, List[Dict[str, Any]]] = {}
    for r in mg:
        mid = r["movie_id"]
        gid = str(r["genre_id"])  
        genre = genres.get(gid)
        if not genre:
            continue
        by_movie_genres.setdefault(mid, []).append({"genre_id": gid, "name": genre["name"]})

    # Yield in batches
    batch: List[Dict[str, Any]] = []
    for m in movies:
        m["people"] = by_movie_people.get(m["movie_id"], [])
        m["genres"] = by_movie_genres.get(m["movie_id"], [])
        batch.append(m)
        if len(batch) >= batch_size:
            yield {"movies": batch}
            batch = []
    if batch:
        yield {"movies": batch}


def stream_person_person(conn, batch_size: int = 5000) -> Iterable[List[Dict[str, Any]]]:
    query = "SELECT person_id_1::text AS p1, person_id_2::text AS p2, rel_type FROM person_person_relationship"
    with conn.cursor(name="pp_cursor", cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.itersize = batch_size
        cur.execute(query)
        while True:
            rows = cur.fetchmany(batch_size)
            if not rows:
                break
            yield rows


def stream_person_genre(conn, batch_size: int = 5000) -> Iterable[List[Dict[str, Any]]]:
    query = "SELECT person_id::text AS p, genre_id::text AS g, rel_type FROM person_genre_relationship"
    with conn.cursor(name="pg_cursor", cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.itersize = batch_size
        cur.execute(query)
        while True:
            rows = cur.fetchmany(batch_size)
            if not rows:
                break
            yield rows


def write_batch(session, batch: Dict[str, List[Dict[str, Any]]]) -> None:
    def tx_fn(tx, movies: List[Dict[str, Any]]):
        # Create/merge movie nodes
        tx.run(
            """
            UNWIND $movies AS m
            MERGE (mov:Movie {movie_id: m.movie_id})
            SET mov.title = m.title,
                mov.year = m.year,
                mov.description = m.description,
                mov.score = m.score
            """,
            movies=movies,
        )
        # Create/merge people and relationships
        tx.run(
            """
            UNWIND $movies AS m
            UNWIND m.people AS p
            MERGE (mov:Movie {movie_id: m.movie_id})
            MERGE (per:Person {person_id: p.person_id})
            SET per.name = p.name
            WITH mov, per, p
            CALL (mov, per, p) {
                WITH mov, per, p
                WHERE p.rel_type = 'DIRECTOR'
                MERGE (per)-[:DIRECTED]->(mov)
            }
            CALL (mov, per, p) {
                WITH mov, per, p
                WHERE p.rel_type = 'ACTOR'
                MERGE (per)-[:ACTED_IN]->(mov)
            }
            """,
            movies=movies,
        )
        # Create/merge genres and relationships
        tx.run(
            """
            UNWIND $movies AS m
            UNWIND m.genres AS g
            MERGE (mov:Movie {movie_id: m.movie_id})
            MERGE (gen:Genre {genre_id: g.genre_id})
            SET gen.name = g.name
            MERGE (mov)-[:HAS_GENRE]->(gen)
            """,
            movies=movies,
        )

    # Neo4j 5+ execute_write
    session.execute_write(tx_fn, batch["movies"])


def write_pp_batch(session, rels: List[Dict[str, Any]]) -> None:
        def tx_fn(tx, rels):
                tx.run(
                        """
                        UNWIND $rels AS r
                        MERGE (p1:Person {person_id: r.p1})
                        MERGE (p2:Person {person_id: r.p2})
                        // Treat these as undirected by storing a single consistent direction
                        FOREACH (_ IN CASE WHEN r.rel_type = 'CO_ACTED_WITH' THEN [1] ELSE [] END |
                            MERGE (p1)-[:CO_ACTED_WITH]->(p2)
                        )
                        FOREACH (_ IN CASE WHEN r.rel_type = 'WORKED_WITH' THEN [1] ELSE [] END |
                            MERGE (p1)-[:WORKED_WITH]->(p2)
                        )
                        """,
                        rels=rels,
                )
        session.execute_write(tx_fn, rels)


def write_pg_batch(session, rels: List[Dict[str, Any]]) -> None:
        def tx_fn(tx, rels):
                tx.run(
                        """
                        UNWIND $rels AS r
                        MERGE (p:Person {person_id: r.p})
                        MERGE (g:Genre {genre_id: r.g})
                        FOREACH (_ IN CASE WHEN r.rel_type = 'ACTS_IN_GENRE' THEN [1] ELSE [] END |
                            MERGE (p)-[:ACTS_IN_GENRE]->(g)
                        )
                        FOREACH (_ IN CASE WHEN r.rel_type = 'DIRECTS_GENRE' THEN [1] ELSE [] END |
                            MERGE (p)-[:DIRECTS_GENRE]->(g)
                        )
                        """,
                        rels=rels,
                )
        session.execute_write(tx_fn, rels)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Import graph tables into Neo4j")
    p.add_argument("--database-url", default=os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL"), help="PostgreSQL connection URL")
    p.add_argument("--sslmode", default=os.getenv("PGSSLMODE", None), help="PostgreSQL sslmode")
    p.add_argument("--host", default=DEFAULT_DB_CONFIG["host"], help="PostgreSQL host")
    p.add_argument("--port", type=int, default=DEFAULT_DB_CONFIG["port"], help="PostgreSQL port")
    p.add_argument("--dbname", default=DEFAULT_DB_CONFIG["dbname"], help="PostgreSQL database name")
    p.add_argument("--user", default=DEFAULT_DB_CONFIG["user"], help="PostgreSQL user")
    p.add_argument("--password", default=DEFAULT_DB_CONFIG["password"], help="PostgreSQL password")
    p.add_argument("--neo4j-uri", default=DEFAULT_NEO4J["uri"], help="Neo4j bolt URI")
    p.add_argument("--neo4j-user", default=DEFAULT_NEO4J["user"], help="Neo4j user")
    p.add_argument("--neo4j-password", default=DEFAULT_NEO4J["password"], help="Neo4j password")
    p.add_argument("--batch-size", type=int, default=1000, help="Batch size for processing movies")
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
        conn = connect_db(db_config)
    except psycopg2.OperationalError as e:
        logging.error("PostgreSQL connection failed: %s", e)
        raise

    try:
        driver = connect_neo4j(args.neo4j_uri, args.neo4j_user, args.neo4j_password)
    except Exception as e:
        logging.error("Neo4j connection failed: %s", e)
        conn.close()
        raise

    total_movies = 0
    total_pp = 0
    total_pg = 0
    try:
        with driver.session() as session:
            for batch in fetch_graph_batches(conn, batch_size=args.batch_size):
                movies_len = len(batch["movies"])
                if movies_len == 0:
                    continue
                logging.info("Processing batch of %d movies", movies_len)
                write_batch(session, batch)
                total_movies += movies_len
            # Person-Person relationships
            for rel_batch in stream_person_person(conn, batch_size=max(1000, args.batch_size)):
                logging.info("Processing person-person batch of %d", len(rel_batch))
                write_pp_batch(session, rel_batch)
                total_pp += len(rel_batch)
            # Person-Genre relationships
            for rel_batch in stream_person_genre(conn, batch_size=max(1000, args.batch_size)):
                logging.info("Processing person-genre batch of %d", len(rel_batch))
                write_pg_batch(session, rel_batch)
                total_pg += len(rel_batch)
    finally:
        driver.close()
        conn.close()

    logging.info(
        "Completed import to Neo4j. Movies=%d person-person=%d person-genre=%d",
        total_movies, total_pp, total_pg
    )


if __name__ == "__main__":
    main()

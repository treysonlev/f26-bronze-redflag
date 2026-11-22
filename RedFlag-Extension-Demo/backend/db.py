# Flask to postgres connection
import os

import psycopg2
from pathlib import Path

# Define the path to the schema file where the database is located
SCHEMA_FILE = (
    Path(__file__).resolve().parents[2]
    / "docker"
    / "init"
    / "01_schema.sql"
)


def get_connection():
    return psycopg2.connect(
        os.getenv(
            "DATABASE_URL",
            "postgresql://redflag:redflag@localhost:5432/redflag",
        )
    )


def init_db_schema():
    """
    Create the database defined in the project's SQL schema
    """
    if not SCHEMA_FILE.is_file():
        raise FileNotFoundError(f"Database schema file not found: {SCHEMA_FILE}")

    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")

    conn = get_connection()
    try:
        # The schema file contains its own BEGIN and COMMIT.
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(schema_sql)
    finally:
        conn.close()




# This is the old init_db() that creats the old 'claims' table, I'm keeping it around
# temporarily for reference
'''
def init_db():
    """Create the claims cache table used by /analyze, if it does not exist.

    The docker init scripts only run on an empty volume, so the backend
    upgrades the schema itself at startup. This table is separate from the
    ERD tables (source/verdict/claim/keyword); it stores one row per LLM
    finding keyed by the analyzed text's hash so repeat scans skip the LLM.
    An empty claim marks text that was analyzed with nothing flagged.
    """
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS claims (
                    id        SERIAL PRIMARY KEY,
                    claim     VARCHAR(1000) NOT NULL,
                    label     VARCHAR(120),
                    reason    VARCHAR(600),
                    text_hash CHAR(64)      NOT NULL,
                    flagtype  VARCHAR(20),
                    sources   JSONB         NOT NULL DEFAULT '[]'::jsonb
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_claims_text_hash "
                "ON claims (text_hash)"
            )
    finally:
        conn.close()
'''
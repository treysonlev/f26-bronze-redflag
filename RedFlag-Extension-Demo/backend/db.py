# Flask to postgres connection
import os

import psycopg2


def get_connection():
    return psycopg2.connect(
        os.getenv(
            "DATABASE_URL",
            "postgresql://redflag:redflag@localhost:5432/redflag",
        )
    )


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

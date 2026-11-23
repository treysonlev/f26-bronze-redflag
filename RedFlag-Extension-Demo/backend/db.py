"""
This module defines all operations made on the database. Database creation,
data retrieval and creation, etc.
"""

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


def init_db():
    """
    Apply the project's SQL schema, including the ERD and extension findings.
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


def insert_data(finding, keywords=None): 
    """
    Define methods to insert data into the database
    """

    if not isinstance(finding, dict):
        raise TypeError("finding must be a dictionary")

    claim_text = finding.get("claim", "").strip()

    if not claim_text:
        raise ValueError("Finding must contain a non-empty claim")

    if len(claim_text) > 255:
        raise ValueError("Claim exceeeds the database's 255-character limit")

    label = finding.get("label", "Needs verification")[:120]
    reason = finding.get("reason", "No explanation provided.")[:600]
    flagtype = finding.get("flagtype", "redflag")
    result = finding.get("result", "unable_to_verify")

    allowed_flagtypes = {"redflag", "biasstar", "signal"}
    allowed_results = {"true", "false", "unable_to_verify"}

    if flagtype not in allowed_flagtypes:
        raise ValueError(f"Invalid flagtype: {flagtype}")

    if result not in allowed_results:
        raise ValueError(f"Invalid result: {result}")

    keywords = keywords or []

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:

                # 1) Insert the claim.
                cur.execute(
                    """
                    INSERT INTO claim (claim, verdict_id)
                    VALUES (%s, NULL)
                    RETURNING claim_id
                    """,
                    (claim_text,)
                )

                claim_id = cur.fetchone()[0]

                # 2) Insert the finding associated with the claim.
                cur.execute(
                    """
                    INSERT INTO finding
                        (claim_id, matched_text, label, reason, flagtype, result)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING finding_id
                    """,
                    (
                        claim_id,
                        claim_text,
                        label,
                        reason,
                        flagtype,
                        result
                    )
                )

                finding_id = cur.fetchone()[0]

                # 3) Insert any keywords.
                for keyword in keywords:
                    keyword = str(keyword).strip()

                    if keyword:
                        cur.execute(
                            """
                            INSERT INTO keyword (claim_id, keyword)
                            VALUES (%s, %s)
                            """,
                            (claim_id, keyword[:50])
                        )
        return {
            "claim_id": claim_id,
            "finding_id": finding_id
        }

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
"""Drop RedFlag project tables so db.init_db() can recreate the schema."""

import os
from pathlib import Path

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCKER_ENV_FILE = PROJECT_ROOT / "docker" / ".env"

# Drop dependents before the tables they reference. Keep this list limited to
# RedFlag tables; do not use CASCADE so unexpected dependencies stop the reset.
TABLES_TO_DROP = (
    "finding",
    "keyword",
    "claim",
    "verdict",
    "source",
    "claims",  # Legacy cache table.
)


def main() -> None:
    load_dotenv(DOCKER_ENV_FILE)
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            f"DATABASE_URL is not set. Set it in {DOCKER_ENV_FILE} "
            "or in the environment."
        )

    conn = psycopg2.connect(database_url)
    try:
        dsn = conn.get_dsn_parameters()
        database = dsn.get("dbname", "(unknown database)")
        host = dsn.get("host") or "local socket"
        port = dsn.get("port") or "5432"
        target = f"{database}@{host}:{port}"

        print("This permanently removes the following RedFlag tables and data:")
        for table in TABLES_TO_DROP:
            print(f"  public.{table}")
        confirmation = input(f'To continue, type "{target}": ')
        if confirmation != target:
            print("Reset cancelled.")
            return

        with conn:
            with conn.cursor() as cur:
                for table in TABLES_TO_DROP:
                    cur.execute(
                        sql.SQL("DROP TABLE IF EXISTS {}").format(
                            sql.Identifier("public", table)
                        )
                    )

        print("RedFlag tables dropped. Run the backend to initialize 01_schema.sql.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

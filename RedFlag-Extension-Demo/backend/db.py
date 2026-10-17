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

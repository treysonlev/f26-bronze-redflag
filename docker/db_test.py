# Bare-bones test: connect to Postgres, insert one row, read it back.
# 1) docker compose up -d   2) cp .env.example .env   3) python3 db_test.py
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Connect to the existing database, then open a cursor to perrform db operations
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# cur.execute("""
#     CREATE TABLE IF NOT EXISTS claims (
#         id SERIAL PRIMARY KEY,
#         claim TEXT NOT NULL,
#         label TEXT,
#         reason TEXT,
#         created_at TIMESTAMPTZ NOT NULL DEFAULT now()
#     )
# """)

cur.execute("SELECT to_regclass('public.claims') IS NOT NULL")
table_exists = cur.fetchone()[0]

if not table_exists:
	print("The claims table does not currently exist.")

cur.execute(
    "INSERT INTO claims (claim, label, reason) VALUES (%s, %s, %s)",
    ("the earth is flat", "Known false claim", "Inserted by db_test.py"),
)

conn.commit()

cur.execute("SELECT COUNT(*) FROM claims")
print("Total rows:", cur.fetchone()[0])

cur.execute("SELECT id, claim, label FROM claims ORDER BY id DESC LIMIT 1")
print("Last row:  ", cur.fetchone())

conn.close()
print("Database test passed.")

# Bare-bones test: connect to Postgres, insert one row, read it back.
# 1) docker compose up -d   2) cp .env.example .env   3) python3 db_test.py
import os

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()

# Connect to the existing database, then open a cursor to perform db operations
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# Function to print the number of rows in each table (mainly for debugging)
def print_row_counts():
	cur.execute("SELECT COUNT(*) FROM claim")
	print("Total rows in CLAIM:", cur.fetchone()[0])
	cur.execute("SELECT COUNT(*) FROM keyword")
	print("Total rows in KEYWORD:", cur.fetchone()[0])
	cur.execute("SELECT COUNT(*) FROM source")
	print("Total rows in SOURCE:", cur.fetchone()[0])
	cur.execute("SELECT COUNT(*) FROM verdict")
	print("Total rows in VERDICT:", cur.fetchone()[0])


# Simulate creating/logging a claim
def create_claim_and_keywords() -> int:
	# First, Create a claim in the CLAIM table
    # claim_id will auto-increment to 1 and verdict_id will be NULL for now
	cur.execute("""
        INSERT INTO claim (claim) 
        VALUES (%(claim)s)
        RETURNING claim_id
        """,
        {'claim': "The Earth is Flat (db_test.py claim)"}
    )
	claim_id = cur.fetchone()[0]

    # Next, insert rows in KEYWORD for the claim created
	for keyword in ("earth", "flat"):
		cur.execute("""
            INSERT INTO keyword (claim_id, keyword)
            VALUES (%(claim_id)s, %(keyword)s)
            """,
            {'claim_id': claim_id, 'keyword': keyword}
        )
	
	conn.commit()
	print(f"Inserted claim with id {claim_id} and its keywords.")
	return claim_id


# Resets the auto-incrementing id counter to the maximum id currently in the table
def reset_id_count(table_name: str, id_column_name: str):
	# Grab the current largest id from the table passed
	cur.execute(
		# The block of code below safely constructs a query equivilant to
		#       SELECT MAX("claim_id") FROM "public"."claim"
		sql.SQL("SELECT MAX({}) FROM {}").format(
			sql.Identifier(id_column_name),
			sql.Identifier("public", table_name)
        )
    )
	max_id = cur.fetchone()[0]
	
	cur.execute("""
        SELECT setval(
            pg_get_serial_sequence(%(table_name)s, %(id_column_name)s),
			%(max_id)s,
			%(is_max_id_none)s
		)
        """,
        {
			'table_name': f"public.{table_name}",
			'id_column_name': id_column_name,
			'max_id': max_id if max_id is not None else 1,
			'is_max_id_none': max_id is not None,
        }
    )




# Verify all necessary tables defined in the schema exist
required_tables = ["source",  "verdict", "claim", "keyword"]

cur.execute("""
    SELECT table_name
	FROM information_schema.tables
	WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
	  AND table_name = ANY(%s)
    """,
    (required_tables,)
)

existing_tables = {row[0] for row in cur.fetchall()}
missing_tables = set(required_tables) - existing_tables

if missing_tables:
	print("Missing tables:", ", ".join(missing_tables))
	conn.close()
	raise SystemExit(1)

print("All required tables exist")

print_row_counts()

# Check to see if the claims table also exists (old table no longer used)
cur.execute("SELECT to_regclass('public.claims') IS NOT NULL")
claims_table_exists = cur.fetchone()[0]

if claims_table_exists:
	print("The claims table currently exists. " \
    "Follow instructions in README.md to remove this outdated table.")



# Remove all rows currently in claims TODO this is unsafe
# cur.execute("TRUNCATE TABLE claim RESTART IDENTITY CASCADE")
# cur.execute("TRUNCATE TABLE verdict RESTART IDENTITY CASCADE")
# cur.execute("TRUNCATE TABLE source RESTART IDENTITY CASCADE")


# Simulate creating/logging a claim
claim_id = create_claim_and_keywords()




# Test verifying the claim that was just created
# Create a row in the SOURCE table
cur.execute("""
    INSERT INTO source (url, excerpt)
	VALUES (%(url)s, %(excerpt)s)
	RETURNING source_id
    """,
    {
		'url': 
        "https://science.feedback.org/review/how-we-know-earth-is-round-not-flat-a-review-of-claims-and-misconceptions-about-earths-shape/", 
        'excerpt': 
        """In 240 B.C.E., the Greek mathematician Eratosthenes estimated that the circumference of the Earth was approximately 24,000 - 29,000 miles by measuring the distance between two cities in Egypt and the angle of the Sun's rays during the summer solstice[1]. Specifically, he noticed that on the summer solstice, a stick located in the city of Syene cast no shadow, whereas a stick in Alexandria cast a shadow at an angle of about 7.2 degrees. This observed difference in shadow angles is only possible if the Earth's surface is curved (Figure 2). (db_test.py source)"""
    }
)
source_id = cur.fetchone()[0]

# Create a row in the VERDICT table with the LLM explanation/evaluation
cur.execute("""
    INSERT INTO verdict (source_id, verdict, explanation, correctness, confidence)
	VALUES (%(source_id)s, %(verdict)s, %(explanation)s, %(correctness)s, %(confidence)s)
	RETURNING verdict_id
    """,
    {
		'source_id': source_id,
		'verdict': False,
		'explanation': 
        """The claim “The Earth is Flat” is incorrect and directly contradicted by the provided source excerpt. The excerpt explains how the Greek mathematician Eratosthenes estimated Earth's circumference around 240 B.C.E. by measuring the distance between two Egyptian cities and comparing the angles of the Sun's rays during the summer solstice. He observed that a stick in Syene cast no shadow, while a stick in Alexandria cast a shadow at an angle of approximately 7.2 degrees. This difference in shadow angles is consistent with a curved Earth and contradicts the claim that Earth is flat. Although the excerpt alone does not constitute a complete modern demonstration of Earth's shape, its described observations provide evidence against the claim. Furthermore, extensive independent scientific evidence, including satellite imagery, circumnavigation, and astronomical observations, confirms that Earth is approximately spherical, more precisely an oblate spheroid. Therefore, the claim receives a correctness score of 0.00 because it is factually false. The confidence level is 1.00 because the claim contradicts both the evidence presented in the excerpt and well-established scientific knowledge. There is virtually no reasonable uncertainty about the correctness of this rating. (db_test.py verdict)""",
		'correctness': 0.00,
		'confidence': 1.00
    }
)
verdict_id = cur.fetchone()[0]

# Update the claim's row in CLAIM with the newly generated verdict_id
cur.execute("""
    UPDATE claim
	SET verdict_id = %(verdict_id)s
	WHERE claim_id = %(claim_id)s
    """,
    {'verdict_id': verdict_id, 'claim_id': claim_id}
)

conn.commit()
print(f"Inserted source with id {source_id} and verdict with id {verdict_id}")


# Display the number of rows in each table
print_row_counts()

cur.execute("SELECT * FROM claim ORDER BY claim_id DESC LIMIT 1")
print("Last row in CLAIM:  ", cur.fetchone())

conn.commit()



# Remove inserted rows from the database
# Remove the claim and its keywords
cur.execute("""
    DELETE FROM claim
	WHERE claim = 'The Earth is Flat (db_test.py claim)'
    """	
)
cur.execute("""
    DELETE FROM verdict
	WHERE verdict_id = %(verdict_id)s
    """,
    {'verdict_id': verdict_id}
)
cur.execute("""
    DELETE FROM source
	WHERE source_id = %(source_id)s
    """,
    {'source_id': source_id}
)

conn.commit()

# Though the rows added by this test have been removed, future entries added
# to these tables will build off of their id's, even though they're gone. For
# example, adding another claim will start claim_id at 2, even though there is
# no claim with claim_id 1 anymore. As such, reset all table's id counters:
reset_id_count("claim", "claim_id")
reset_id_count("keyword", "keyword_id")
reset_id_count("source", "source_id")
reset_id_count("verdict", "verdict_id")

conn.commit()
print("All rows added by this test have been removed")


# cur.execute("""
    
#     """	
# )

conn.close()
print("Database test passed.")

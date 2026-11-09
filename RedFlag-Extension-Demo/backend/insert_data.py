"""
This module contains helper functions that will insert testing data into the database.
"""
from db import get_connection



def insert_test_data():
    """
    Insert a number of example claims, keywords, sources, and verdicts.
    
    Returns:
    int: The total number of rows inserted
    """

    conn = get_connection()

    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO source (url, excerpt)
            VALUES (%s, %s)
            RETURNING source_id
            """,
            (
                "https://example.com/test",
                "An example webpage excerpt used for database testing."
            )
        )

        source_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO verdict
                (source_id, verdict, explanation, correctness, confidence)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING verdict_id
            """,
            (
                source_id,
                False,
                "This is an example test verdict.",
                0.95,
                0.90
            )
        )

        verdict_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO claim (claim, verdict_id)
            VALUES (%s, %s)
            RETURNING claim_id
            """,
            (
                "The Earth is flat.",
                verdict_id
            )
        )

        claim_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO keyword (claim_id, keyword)
            VALUES (%s, %s)
            """,
            (claim_id, "Earth")
        )

        conn.commit()

        return 4

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    return 0



if __name__ == "__main__":
    try:
        count = insert_test_data()
        print(f"Successfully inserted {count} rows!")

    except Exception as error:
        print("Database insertion failed:", error)
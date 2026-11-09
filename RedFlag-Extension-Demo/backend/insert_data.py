"""
This module contains helper functions that will insert testing data into the database.
"""
from db import get_connection

# Connect to the existing database, then open a cursor to perform db operations

cur = conn.cursor()

TEST_RECORDS = [
    {
        "url": "https://science.feedback.org/review/how-we-know-earth-is-round-not-flat-a-review-of-claims-and-misconceptions-about-earths-shape/",
        "excerpt": "In 240 B.C.E., the Greek mathematician Eratosthenes estimated that the circumference of the Earth was approximately 24,000 - 29,000 miles by measuring the distance between two cities in Egypt and the angle of the Sun's rays during the summer solstice[1]. Specifically, he noticed that on the summer solstice, a stick located in the city of Syene cast no shadow, whereas a stick in Alexandria cast a shadow at an angle of about 7.2 degrees. This observed difference in shadow angles is only possible if the Earth's surface is curved (Figure 2).",
        "verdict": False,
        "explanation": "The claim “The Earth is Flat” is incorrect and directly contradicted by the provided source excerpt. The excerpt explains how the Greek mathematician Eratosthenes estimated Earth's circumference around 240 B.C.E. by measuring the distance between two Egyptian cities and comparing the angles of the Sun's rays during the summer solstice. He observed that a stick in Syene cast no shadow, while a stick in Alexandria cast a shadow at an angle of approximately 7.2 degrees. This difference in shadow angles is consistent with a curved Earth and contradicts the claim that Earth is flat. Although the excerpt alone does not constitute a complete modern demonstration of Earth's shape, its described observations provide evidence against the claim. Furthermore, extensive independent scientific evidence, including satellite imagery, circumnavigation, and astronomical observations, confirms that Earth is approximately spherical, more precisely an oblate spheroid. Therefore, the claim receives a correctness score of 0.00 because it is factually false. The confidence level is 1.00 because the claim contradicts both the evidence presented in the excerpt and well-established scientific knowledge. There is virtually no reasonable uncertainty about the correctness of this rating. (db_test.py verdict)",
        "correctness": 0.00,
        "confidence": 1.00,
        "claim": "The Earth is flat.",
        "keywords": ["earth", "flat"],
    },
    {
        "url": "",
        "excerpt": "",
        "verdict": False,
        "explanation": "",
        "correctness": "",
        "confidence": "",
        "claim": "", 
        "keywords": [],
        
    }
    
]


def find_all_missing_tables() -> set[str]:
    """
    Finds any and all missing tables within the database

    Returns:
    set[str]: The set of all database tables that are required and not present
    """
    required_tables = ["source",  "verdict", "claim", "keyword"]

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
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
        
        return missing_tables
    except Exception:
        raise
        

def insert_test_data() -> int:
    """
    Insert a number of example claims, keywords, sources, and verdicts.
    
    Returns:
    int: The total number of records inserted
    """
    conn = get_connection()
    inserted = 0
    
    # First, ensure that all required tables are present
    missing_tables = find_all_missing_tables()
    if (missing_tables):
        print("Missing tables:", ", ".join(missing_tables))
        conn.close()
        return 0
    
    # Insert data in foreign-key order: source -> verdict -> claim -> keyword
    # The connection context commits on success and rolls back on error.
    try: 
        with conn:
            with conn.cursor() as cursor:
                inserted += 0
                # TODO Insert the test records into the database
    finally:
        conn.close()
    
    return inserted




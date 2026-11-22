# Deprecated
# Important
.env holds the API key and endpoint, never commit and push these

# Resetting the RedFlag database

`reset_database.py` drops the RedFlag tables (including the legacy `claims`
cache) and their data. It reads `DATABASE_URL` from `docker/.env`, or from the
environment, and requires typing the connected database target before it
proceeds. Ensure the docker container is running first.

From the repository root, install the script requirements if needed and run:

```
python -m pip install -r Scripts/requirements.txt
python Scripts/reset_database.py
```

The script only drops the tables; it does not recreate them. Start the backend
afterward so `init_db()` applies `docker/init/01_schema.sql`.

# How to use
## Requirements
1) Have pip and python3 installed
2) Run in a terminal: `pip install -r requirements.txt`

## Usage
1) Create a .env file by copying .env.example and using the real API endpoint and token.
2) Modify the query manually in the query.py file by changing the user content text.
    * You may also try changing the temperature, which changes how predictable the LLM will be, from 0 as reliable to 1 as random or more creative.
    * Increase the token count if you're asking for a big output or nothing is coming back from your prompt.
3) Run in a terminal: `python3 query.py`

python3 query.py

# Notes
Models can be found on llm.cs.odu.edu

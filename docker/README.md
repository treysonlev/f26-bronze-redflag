# Docker setup (Postgres)

## Requirements
- Docker
- Python

## Usage
1) cp .env.example .env
2) docker compose up -d      # pulls postgres:16-alpine and starts it
3) docker compose ps         # confirm the db shows "running", then wait a few seconds
4) python3 db_test.py        # needs: pip install psycopg2-binary python-dotenv
5) docker compose down       # stops it (volume for the local container will persist)


## Troubleshooting
To connect to the db in your local terminal (cd to docker folder) and run 
1) docker exec -it redflag-db psql -U redflag -d redflag 
Any SQL statement / command can be run on the local database inside this interactive shell
1) \l 					# list all databases
2) \dt 					# lists all tables in the current database
3) \c database_name		# connects/switches to a different database
4) \d table_name		# Describe a table's structure
5) \q 					# quit psql

To remove the CLAIMS table from your local database, run the following command in psql:
1) DROP TABLE IF EXISTS claims;

To remove all rows from the CLAIMS table, run the following command in psql:
1) DELETE FRROM claims;

To re-apply the schema defined in 01_schema.sql, run the following commands:
1) docker compose up -d db 													# Ensures PostgreSQL is running
2) docker compose cp .\init\01_schema.sql db:/tmp/01_schema.sql 			# Copies schema file into the container
3) docker compose exec db psql -U redflag -d redflag -f /tmp/01_schema.sql 	# Runs schema file against the redflag db

You can verify the table exists with the command below. If it does exist, it should print "claims"
4) docker compose exec db psql -U redflag -d redflag -c "SELECT to_regclass('public.claims');"	
		
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
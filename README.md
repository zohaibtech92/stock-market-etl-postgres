# Stock Market ETL Pipeline → PostgreSQL

A production-style ETL pipeline that pulls daily stock price data via yfinance,
validates and transforms it, and loads it into a PostgreSQL database using a
proper star schema (fact + dimension tables) — not a flat table.

## Why this project
Previous ETL work (USD-to-INR exchange rate tracker) used SQLite and a single
flat table. This project is a deliberate step up: a real relational database,
a normalized schema, and idempotent loads that can be re-run safely on a
schedule without creating duplicate data.

## Tech stack
- Python 3
- PostgreSQL 18 (running natively in WSL Ubuntu)
- SQLAlchemy + psycopg2 for the database layer
- yfinance for data extraction
- pandas for transformation
- python-dotenv for credential management

## Progress log

### Step 1 — Environment setup
- Installed PostgreSQL 18 in WSL Ubuntu via `apt`
- Created a dedicated non-superuser role (`stock_etl_user`) and database
  (`stock_market`) rather than using the default `postgres` superuser
- Set up a Python virtual environment with the required libraries
- Verified the Python → PostgreSQL connection with a standalone test script
- Credentials stored in `.env`, excluded from version control via `.gitignore`

**Note on WSL:** PostgreSQL does not auto-start on WSL boot the way it would
on a normal Linux install — it has to be started manually with
`sudo service postgresql start` at the beginning of each new terminal session.

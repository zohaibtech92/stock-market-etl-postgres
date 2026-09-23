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

### Step 2 — Schema design (star schema)
Designed and implemented a star schema instead of a single flat table:

- **`dim_company`** — one row per stock ticker (company name, sector, exchange).
  Descriptive attributes that rarely change, stored once rather than repeated
  on every price row.
- **`dim_date`** — one row per calendar date, with pre-computed year/month/
  day-of-week/is_weekend fields. Standard data-warehousing convention that
  makes time-based aggregation (e.g. "average close price by month") a simple
  join instead of repeated date-function calls.
- **`fact_stock_prices`** — one row per (company, date), holding only OHLCV
  measurements and foreign keys into the two dimensions above.

Design decisions worth noting:
- Used `NUMERIC(12,4)` instead of `FLOAT` for all price columns — floats
  introduce rounding error that's a real problem for financial data.
- Added a `UNIQUE (company_id, date_id)` constraint on the fact table. This
  is what makes the pipeline **idempotent** — rerunning the load for a date
  that's already loaded won't create a duplicate row (handled via upsert
  logic in the load step).
- Enforced referential integrity with `REFERENCES` foreign keys — a price
  row physically cannot be inserted for a company that doesn't exist in
  `dim_company`. SQLite (used in the earlier exchange-rate project) doesn't
  enforce this by default, which was part of the motivation for this project.

Verified schema creation with `psql ... -f schema.sql` and confirmed all
three tables exist via `\dt`.

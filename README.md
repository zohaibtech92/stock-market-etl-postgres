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

### Step 3 — Populate dim_date
Populated the date dimension using PostgreSQL's `generate_series()` to
generate a full calendar range (2020-01-01 to 2027-12-31, 2,922 rows) in a
single SQL statement rather than looping through dates in Python.

Bug encountered: `generate_series(...) AS d` alone doesn't expose `d` as a
usable column reference in the SELECT list — Postgres requires the fuller
form `AS d(d)` to explicitly name the output column. Fixed and reran.

Each row precomputes year, month, day, day-of-week name, and an is_weekend
boolean (via `EXTRACT(ISODOW FROM d) IN (6, 7)`), so future analytical
queries (e.g. average close price by month) can join against this table
instead of repeating date-function calls on every query.

Note: `TO_CHAR(d, 'Day')` pads weekday names to a fixed width (trailing
spaces) — not an issue for storage, but would need `TRIM()` if ever used in
an exact-match WHERE clause.

### Step 4 — Extract script (yfinance)
Wrote `extract.py` to pull daily OHLCV data for a fixed ticker list
(AAPL, MSFT, GOOGL, TSLA, AMZN) via yfinance, combining each ticker's
result into a single pandas DataFrame.

Bug encountered: script failed with `ModuleNotFoundError: No module named
'yfinance'` when the virtual environment wasn't activated — yfinance was
installed inside `venv`, not globally. Fixed by remembering to run
`source venv/bin/activate` at the start of every terminal session before
running any project script.

Confirmed yfinance's raw column names: Date, Open, High, Low, Close, Volume,
Dividends, Stock Splits, ticker. Dividends/Stock Splits aren't part of this
project's schema and will be dropped in the transform step. The Date column
also carries a timezone offset that needs stripping before it can be joined
against `dim_date.full_date`.

### Step 5 — Transform & validate
Wrote `transform.py` to clean raw yfinance output into the exact shape of
`fact_stock_prices`:
- Dropped unused columns (Dividends, Stock Splits)
- Stripped timezone info from the Date column, keeping only the calendar date
- Renamed columns to match the database schema (open_price, high_price, etc.)
- Added real data-quality checks, not just type conversion:
  - Drops rows with nulls in any critical price/volume field
  - Drops rows where high < low (should be mathematically impossible for
    real market data — signals bad source data if it happens)
  - Drops rows with non-positive prices
  - Drops rows with negative volume

All 25 extracted rows passed validation on this run (0 dropped), confirming
the checks aren't overly aggressive on clean data — the real test will be
seeing whether they correctly catch bad data if/when the API returns any.

### Step 6 — Load (idempotent upsert into PostgreSQL)
Wrote `load.py` using SQLAlchemy to upsert data into `dim_company` and
`fact_stock_prices`, keyed on `UNIQUE(ticker)` and `UNIQUE(company_id, date_id)`
respectively via `ON CONFLICT ... DO UPDATE`.

Bugs encountered:
1. Connection string built with plain f-string concatenation broke when the
   database password contained an `@` character — SQLAlchemy parsed part of
   the password as the hostname (`could not translate host name "786@localhost"`).
   Fixed by URL-encoding user/password with `urllib.parse.quote_plus()`
   before building the connection string — the correct general fix for any
   password containing special characters (@, :, /, #).
2. Yahoo Finance's API intermittently fails to fetch its session
   cookie/crumb ("Cookie/crumb fetch failed (Timeout)"), causing some
   tickers to return no data on a given run. Not a code bug — an external
   API being flaky. The Step 4 `if not all_data` guard means the pipeline
   degrades gracefully (loads whatever tickers succeeded) instead of
   crashing entirely.

Verified idempotency across two real consecutive runs: the first run loaded
10 rows (2 companies succeeded). The second run — under the same API
flakiness, with one additional company succeeding this time — correctly
upserted the 10 existing rows in place (refreshed `loaded_at`, no
duplicates) and inserted exactly 5 new rows for the new company. Final
count: 15, confirming `ON CONFLICT` prevents duplicate rows even under
partial, inconsistent API failures run-to-run.

### Step 7a — Orchestration + logging
Wrote `run_pipeline.py` to chain extract → transform → load into a single
entry point, using Python's `logging` module instead of print statements.
Logs write to both the terminal and `pipeline.log` simultaneously (appending
across runs, giving a running history), with full tracebacks captured on
failure via `exc_info=True`, and the pipeline still re-raises after logging
so a scheduler correctly sees a non-zero exit code on failure.

Minor bugs caught and fixed: a missing `f` prefix on one log line (printed
the literal `{len(raw)}` instead of substituting the value), and a missing
space in the log format string. Both cosmetic but worth catching, since log
readability matters once nobody's watching the terminal live.

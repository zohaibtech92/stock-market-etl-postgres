import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd

load_dotenv()

def get_engine():
    user = quote_plus(os.getenv("DB_USER"))
    password = quote_plus(os.getenv("DB_PASSWORD"))
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    dbname = os.getenv("DB_NAME")

    conn_str = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(conn_str)

def upsert_companies(engine, tickers):
    """
    Ensures every ticker has a row in dim_company.
    Returns a dict mapping ticker -> company_id.
    """
    with engine.begin() as conn:
        for ticker in tickers:
            conn.execute(text("""
                INSERT INTO dim_company (ticker, company_name, sector, exchange)
                VALUES (:ticker, :ticker, NULL, NULL)
                ON CONFLICT (ticker) DO NOTHING
            """), {"ticker": ticker})

        result = conn.execute(text("SELECT ticker, company_id FROM dim_company"))
        return {row.ticker: row.company_id for row in result}


def get_date_ids(engine):
    """
    Returns a dict mapping date -> date_id for every row in dim_date.
    """
    with engine.begin() as conn:
        result = conn.execute(text("SELECT full_date, date_id FROM dim_date"))
        return {row.full_date: row.date_id for row in result}


def load_fact_prices(engine, df: pd.DataFrame):
    """
    Upserts transformed OHLCV rows into fact_stock_prices.
    """
    company_map = upsert_companies(engine, df["ticker"].unique().tolist())
    date_map = get_date_ids(engine)

    df = df.copy()
    df["company_id"] = df["ticker"].map(company_map)
    df["date_id"] = df["full_date"].map(date_map)

    missing_dates = df[df["date_id"].isna()]
    if not missing_dates.empty:
        print(f"  Warning: {len(missing_dates)} rows have dates outside dim_date range, dropping")
        df = df.dropna(subset=["date_id"])

    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT INTO fact_stock_prices
                    (company_id, date_id, open_price, high_price, low_price, close_price, volume)
                VALUES
                    (:company_id, :date_id, :open_price, :high_price, :low_price, :close_price, :volume)
                ON CONFLICT (company_id, date_id) DO UPDATE SET
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume,
                    loaded_at = NOW()
            """), {
                "company_id": int(row["company_id"]),
                "date_id": int(row["date_id"]),
                "open_price": row["open_price"],
                "high_price": row["high_price"],
                "low_price": row["low_price"],
                "close_price": row["close_price"],
                "volume": int(row["volume"]),
            })

    print(f"Loaded {len(df)} rows into fact_stock_prices")


if __name__ == "__main__":
    from extract import extract_stock_data, TICKERS
    from transform import transform_stock_data

    raw = extract_stock_data(TICKERS)
    clean = transform_stock_data(raw)

    engine = get_engine()
    load_fact_prices(engine, clean)

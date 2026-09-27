import pandas as pd

REQUIRED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume", "ticker"]

def transform_stock_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and validates raw yfinance data into a shape ready for loading.
    """
    df = df.copy()

    # 1. Keep only the columns we actually need
    df = df[REQUIRED_COLUMNS]

    # 2. Strip timezone info, keep only the calendar date
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

    # 3. Rename columns to match fact_stock_prices schema
    df = df.rename(columns={
        "Date": "full_date",
        "Open": "open_price",
        "High": "high_price",
        "Low": "low_price",
        "Close": "close_price",
        "Volume": "volume",
    })

    # 4. Validation checks
    before = len(df)

    # Drop rows with any nulls in critical columns
    df = df.dropna(subset=["open_price", "high_price", "low_price", "close_price", "volume"])

    # Sanity check: high should never be less than low
    invalid_hl = df[df["high_price"] < df["low_price"]]
    if not invalid_hl.empty:
        print(f"  Warning: dropping {len(invalid_hl)} rows where high < low")
        df = df[df["high_price"] >= df["low_price"]]

    # Sanity check: prices should be positive
    price_cols = ["open_price", "high_price", "low_price", "close_price"]
    invalid_price = df[(df[price_cols] <= 0).any(axis=1)]
    if not invalid_price.empty:
        print(f"  Warning: dropping {len(invalid_price)} rows with non-positive prices")
        df = df[(df[price_cols] > 0).all(axis=1)]

    # Volume should be non-negative
    df = df[df["volume"] >= 0]

    after = len(df)
    print(f"Transform: {before} rows in, {after} rows out ({before - after} dropped)")

    return df


if __name__ == "__main__":
    from extract import extract_stock_data, TICKERS

    raw = extract_stock_data(TICKERS)
    clean = transform_stock_data(raw)
    print(clean.head(10))
    print(f"\nData types:\n{clean.dtypes}")

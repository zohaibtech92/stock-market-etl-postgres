import yfinance as yf
import pandas as pd

TICKERS = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]

def extract_stock_data(tickers, period="5d"):
	"""
	Pulls daily OHLCV data for each ticker using yfinance.
	Returns a single combined pandas DataFrame with a 'ticker' colum added.
	"""
	all_data = []

	for ticker in tickers:
		print(f"Fetching {ticker}...")
		stock = yf.Ticker(ticker)
		hist = stock.history(period=period)

		if hist.empty:
			print(f" Warning: no data returned for {ticker}")
			continue

		hist = hist.reset_index()
		hist["ticker"] = ticker
		all_data.append(hist)

	combined = pd.concat(all_data, ignore_index=True)
	return combined

if __name__ == "__main__":
	df = extract_stock_data(TICKERS)
	print(df.head(10))
	print(f"\nTotal rows: {len(df)}")
	print(f"\nColumns: {list(df.columns)}")

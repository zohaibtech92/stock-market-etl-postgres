import logging
from datetime import datetime

from extract import extract_stock_data, TICKERS
from transform import transform_stock_data
from load import get_engine, load_fact_prices

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s [%(levelname)s] %(message)s",
	handlers=[
		logging.FileHandler("pipeline.log"),
		logging.StreamHandler()
	]
)
logger = logging.getLogger(__name__)

def run_pipeline():
	start_time = datetime.now()
	logger.info("Pipeline run started")

	try:
		logger.info(f"Extracting data for tickers: {TICKERS}")
		raw = extract_stock_data(TICKERS)
		logger.info(f"Extracted {len(raw)} raw rows")

		clean = transform_stock_data(raw)
		logger.info(f"Transformed to {len(clean)} clean rows")

		engine = get_engine()
		load_fact_prices(engine, clean)
		logger.info("Load completed successfully")

	except Exception as e:
		logger.error(f"Pipeline failed: {e}", exc_info=True)
		raise

	finally:
		duration = (datetime.now() - start_time).total_seconds()
		logger.info(f"Pipeline run finished in {duration:.2f} seconds")

if __name__ == "__main__":
	run_pipeline()

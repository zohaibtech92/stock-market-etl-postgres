CREATE TABLE dim_company (
	company_id	SERIAL PRIMARY KEY,
	ticker		VARCHAR(10) NOT NULL UNIQUE,
	company_name	VARCHAR(255),
	sector		VARCHAR(100),
	exchange	VARCHAR(50),
	created_at	TIMESTAMP DEFAULT NOW()
);

CREATE TABLE dim_date (
	date_id		SERIAL PRIMARY KEY,
	full_date	DATE NOT NULL UNIQUE,
	year		INT NOT NULL,
	month		INT NOT NULL,
	day		INT NOT NULL,
	day_of_week	VARCHAR(10) NOT NULL,
	is_weekend	BOOLEAN NOT NULL
);

CREATE TABLE fact_stock_prices (
	fact_id		SERIAL PRIMARY KEY,
	company_id	INT NOT NULL REFERENCES dim_company(company_id),
	date_id		INT NOT NULL REFERENCES dim_date(date_id),
	open_price	NUMERIC(12,4),
	high_price	NUMERIC(12,4),
	low_price	NUMERIC(12,4),
	close_price	NUMERIC(12,4),
	volume		BIGINT,
	loaded_at	TIMESTAMP DEFAULT NOW(),
	UNIQUE (company_id, date_id)
);


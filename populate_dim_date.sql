INSERT INTO dim_date (full_date, year, month, day, day_of_week, is_weekend)
SELECT
    d::date AS full_date,
    EXTRACT(YEAR FROM d)::INT AS year,
    EXTRACT(MONTH FROM d)::INT AS month,
    EXTRACT(DAY FROM d)::INT AS day,
    TO_CHAR(d, 'Day') AS day_of_week,
    EXTRACT(ISODOW FROM d) IN (6, 7) AS is_weekend
FROM generate_series('2020-01-01'::date, '2027-12-31'::date, '1 day'::interval) AS d(d);

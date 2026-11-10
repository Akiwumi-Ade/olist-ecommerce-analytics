# Brazilian E-Commerce Analytics

An end-to-end portfolio project built on the Brazilian Olist marketplace dataset. It demonstrates a repeatable Python/Pandas ingestion pipeline, a constrained PostgreSQL relational model, SQL business analytics, data-quality checks, and an interactive Streamlit dashboard.

## What it answers

- How are orders, gross merchandise value, freight, and average order value changing over time?
- Which product categories and states contribute the most sales?
- How quickly are orders delivered, and how often do they arrive late?
- How do review scores relate to delivery performance?

## Stack

Python 3.9+, Pandas, PostgreSQL, SQLAlchemy/psycopg, SQL, Streamlit, Plotly, Pytest, Git.
The pipeline loads in chunks, and the dashboard queries aggregates from PostgreSQL rather than loading the million-row geolocation table into app memory.

## Dataset

Download/extract the public Olist Brazilian E-Commerce dataset. The expected nine files are:

`olist_customers_dataset.csv`, `olist_geolocation_dataset.csv`, `olist_order_items_dataset.csv`, `olist_order_payments_dataset.csv`, `olist_order_reviews_dataset.csv`, `olist_orders_dataset.csv`, `olist_products_dataset.csv`, `olist_sellers_dataset.csv`, and `product_category_name_translation.csv`.

Keep the source files outside Git. Set `DATA_DIR` to their directory in `.env`, or pass `--data-dir` to the ETL. A `.env.example` is provided. This project does not modify source CSV files.

## Local setup (M1 friendly)

1. Install PostgreSQL 15 or newer and start the local server. Create an empty database named `olist` (or use another name and update the URL).
2. From this project directory, create and activate the project's isolated Anaconda/conda environment, then install its dependencies:

   ```bash
   conda env create -f environment.yml
   conda activate olist-analytics
   ```

   Copy `.env.example` to `.env` only if `.env` does not already exist, then set its paths and database URL. The local `.env` is ignored by Git.

3. Edit `.env` and set `DATA_DIR` and `DATABASE_URL` for your machine.
4. Load the dataset (the reload is transactional and replaces only the project's target tables):

   ```bash
   python -m olist_analytics.etl
   # or: olist-etl --data-dir /path/to/archive
   ```

5. Start the dashboard:

   ```bash
   streamlit run app.py
   ```

Run the tests with `pytest`. They cover source-file discovery, transformation rules, and SQL data-quality checks.

## Model and pipeline

The `public` schema contains normalized source entities: customers, sellers, products, category translations, orders, order items, payments, reviews, and geolocation. Primary keys and foreign keys are created from `sql/schema.sql`; reviews use the composite key `(review_id, order_id)` because the source reuses `review_id` across different orders. CSVs load in dependency order using bounded chunks. The ETL validates required files and columns, parses dates/numbers, checks key uniqueness and referential integrity, then refreshes the tables.

`sql/analytics.sql` creates two query-ready views: `analytics.order_line_facts` (one row per order item, with customer, product, seller, delivery, payment, and review context) and `analytics.monthly_sales` (monthly KPI aggregates). The Streamlit app uses read-only SQL queries against these views.

## Data quality

The ETL fails before replacing database contents if source files, required columns, primary-key uniqueness, or foreign-key relationships are invalid. After loading, SQL checks report row counts, duplicate keys, orphan relationships, invalid review scores, and negative monetary values. Expected blanks in optional delivery timestamps and product attributes are retained as nulls.

## Suggested GitHub presentation

Commit the code, SQL, tests, and documentation. Keep `.env`, credentials, and original CSV files out of Git. Add screenshots of the dashboard after the first successful load. Do not publish a remote repository until its destination is chosen.

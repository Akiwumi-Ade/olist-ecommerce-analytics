# Brazilian E-Commerce Analytics

**An end-to-end data engineering and analytics portfolio project** using public data from Brazil's Olist marketplace.

I built a reproducible pipeline that takes nine raw CSV files, validates and loads them into a relational PostgreSQL database, and turns them into SQL analytics views and an interactive dashboard. The project explores marketplace sales, delivery performance, and customer experience across nearly 100,000 orders.

## What the project delivers

- A **Python and Pandas ETL pipeline** that checks the input files, parses dates and numeric fields, and loads tables in foreign-key order.
- A **relational PostgreSQL model** with primary keys, foreign keys, and indexes for the Olist data.
- **SQL analytics views** that combine order, item, customer, product, seller, payment, delivery, and review information.
- **Data-quality checks and automated tests** for the required source files and columns, duplicate keys, broken relationships, and invalid values.
- A **Streamlit dashboard** with Plotly charts and a month-range filter for exploring sales, product categories, customer locations, delivery outcomes, and review scores.

## Questions explored

- How do order volume and merchandise sales change over time?
- Which product categories and customer states contribute most to merchandise value?
- How long do orders take to arrive, and how often do they arrive after the estimated date?
- How does delivery performance relate to customer review scores?

## Data source and attribution

Data source: Olist, [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), listed on Kaggle under the **CC BY-NC-SA 4.0** license. This repository contains the project code and documentation; the source CSV files are not included. The repository has no separate license for its code yet, and any future code license should remain distinct from the dataset's terms.

## Project at a glance

The local run represented in this project loaded **99,441 orders** from nine source CSVs, including **112,650 order items**, **103,886 payments**, and **99,224 reviews**. The analysis covers 24 monthly periods and 98,199 eligible orders. Nine database quality checks and eight automated tests passed in the current codebase.

These counts describe the dataset version used for the local run; they are not live marketplace figures. The original [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) is distributed separately and is not stored in this repository.

## Selected findings

- **November 2017** was the highest-GMV month, at approximately **R$1.00 million**.
- **Health and beauty** was the largest product category by GMV, at approximately **R$1.26 million**. São Paulo (SP) led customer-state GMV at approximately **R$5.16 million**.
- Among delivered orders with both dates, the average elapsed delivery time was **12.6 days** and **6.8%** arrived after the estimated calendar date.
- The late-delivery rate was **36.8%** for delivered orders with an average review score of 1, compared with **1.9%** for score 5. This is a descriptive relationship in the dataset, not evidence that late delivery alone caused a low review.

These are descriptive results from this dataset version. The dashboard lets readers explore the measures by month, category, state, delivery outcome, and review score.

## How it works

```mermaid
flowchart LR
    A[Olist CSV files] --> B[Python and Pandas ETL]
    B --> C[Input validation]
    C --> D[(PostgreSQL relational tables)]
    D --> E[SQL analytics views]
    E --> F[Streamlit dashboard]
    F --> G[Plotly charts and KPIs]
    D --> H[Database quality checks]
```

The ETL checks the expected inputs before changing the database. It refreshes the project tables in a transaction, so a failed load rolls back instead of leaving a partial refresh. Inserts are chunked to keep the workflow practical on a lightweight local machine. Source CSV files are read-only inputs.

## Data model and analytical layer

The PostgreSQL `public` schema contains customers, sellers, products, category translations, orders, order items, payments, reviews, and geolocation. Foreign keys preserve relationships between orders and customers, and between orders and their items, payments, and reviews.

The source reuses `review_id` for multiple orders, so the review table uses the composite key `(review_id, order_id)`. Geolocation contains multiple coordinates for some postal prefixes; the model preserves those records rather than arbitrarily selecting one.

The SQL layer separates order-level measures from item-level dimensions to prevent payment and review totals from being repeated across an order's item rows. It creates three views:

- `analytics.order_facts`: one row per order with item and freight totals, payment total, review score, customer, and delivery context.
- `analytics.order_line_facts`: one row per order item with customer, product, category, seller, price, and freight context.
- `analytics.monthly_sales`: a monthly summary of orders, buyers, merchandise value, freight, and average order value.

## Dashboard measures

All dashboard panels follow the selected order-month range.

- **GMV** is item price before freight; canceled and unavailable orders are excluded.
- **Average order value** includes item price and freight and is weighted across eligible orders in the selected range.
- **Unique buyers** counts distinct customers across the full range.
- **Late delivery** means arrival on a calendar date after the estimated date, among delivered orders with an estimate.
- **Review score** is averaged per order before comparing it with delivery outcomes.

## Tools and skills demonstrated

Python · Pandas · PostgreSQL · SQL · SQLAlchemy · Streamlit · Plotly · Pytest · Git

This project demonstrates data ingestion, schema design, transactional loading, SQL modeling, data validation, analytical dashboarding, and reproducible project setup.

## Run locally

The following steps reproduce the project on macOS with Anaconda and PostgreSQL.

1. Install and start PostgreSQL, then create a database named `olist`.
2. Create and activate the Conda environment:

   ```bash
   conda env create -f environment.yml
   conda activate olist-analytics
   ```

3. Copy `.env.example` to `.env`, then set the location of the nine Olist CSV files and the database connection URL. With the default Postgres.app setup, the database user is usually your macOS account name:

   ```ini
   DATA_DIR=/path/to/olist-csv-folder
   DATABASE_URL=postgresql+psycopg://your_mac_username@localhost:5432/olist
   ```

4. Load the source data and build the analytics views:

   ```bash
   python -m olist_analytics.etl
   ```

5. Check the project and start the dashboard:

   ```bash
   pytest
   streamlit run app.py
   ```

The `.env` file, downloaded data, Python caches, and build metadata are excluded from Git. The ETL replaces only the project's target tables in the configured database.

## Repository structure

```text
app.py                       Streamlit dashboard
src/olist_analytics/         ETL, configuration, and quality checks
sql/schema.sql               Relational tables, constraints, and indexes
sql/analytics.sql            Dashboard-ready SQL views
tests/                       Automated tests
environment.yml              Conda environment definition
```

"""Streamlit dashboard for the Olist PostgreSQL analytics model."""
from __future__ import annotations

import os
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="Olist Commerce Analytics", page_icon="🛒", layout="wide")
st.title("Brazilian E-Commerce Analytics")
st.caption("Olist marketplace operations, sales, delivery, and customer experience")

@st.cache_resource
def engine_for(url: str):
    return create_engine(url, pool_pre_ping=True)

url = os.getenv("DATABASE_URL")
if not url:
    st.error("Set DATABASE_URL in .env before launching the dashboard.")
    st.stop()
engine = engine_for(url)
try:
    months = pd.read_sql(text("SELECT min(order_month) AS min_month, max(order_month) AS max_month FROM analytics.monthly_sales"), engine)
    if months.empty or pd.isna(months.iloc[0, 0]):
        st.info("No analytics data yet. Run the ETL pipeline first.")
        st.stop()
    monthly = pd.read_sql(text("SELECT * FROM analytics.monthly_sales ORDER BY order_month"), engine)
    states = pd.read_sql(text("""SELECT c.customer_state AS state, count(DISTINCT o.order_id) AS orders,
        sum(i.price) AS gmv FROM orders o JOIN customers c USING(customer_id)
        JOIN order_items i USING(order_id) WHERE o.order_status NOT IN ('canceled','unavailable')
        GROUP BY 1 ORDER BY gmv DESC"""), engine)
    categories = pd.read_sql(text("""SELECT COALESCE(ct.product_category_name_english,p.product_category_name,'Unknown') AS category,
        sum(i.price) AS gmv FROM order_items i JOIN products p USING(product_id)
        LEFT JOIN category_translation ct USING(product_category_name)
        JOIN orders o USING(order_id) WHERE o.order_status NOT IN ('canceled','unavailable')
        GROUP BY 1 ORDER BY gmv DESC LIMIT 12"""), engine)
    delivery = pd.read_sql(text("""SELECT order_status, count(*) AS orders,
        avg(EXTRACT(EPOCH FROM (order_delivered_customer_date-order_purchase_timestamp))/86400.0) AS avg_days,
        avg((order_delivered_customer_date > order_estimated_delivery_date)::int)*100 AS late_pct
        FROM orders WHERE order_delivered_customer_date IS NOT NULL GROUP BY 1 ORDER BY orders DESC"""), engine)
except Exception as exc:
    st.error(f"Could not query the analytics database: {exc}")
    st.stop()

st.sidebar.header("Date range")
min_date, max_date = pd.to_datetime(monthly.order_month.min()).date(), pd.to_datetime(monthly.order_month.max()).date()
date_range = st.sidebar.date_input("Order month", value=(min_date, max_date), min_value=min_date, max_value=max_date)
if isinstance(date_range, tuple) and len(date_range) == 2:
    monthly = monthly[(pd.to_datetime(monthly.order_month).dt.date >= date_range[0]) & (pd.to_datetime(monthly.order_month).dt.date <= date_range[1])]

if monthly.empty:
    st.warning("No data in the selected date range.")
    st.stop()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Orders", f"{int(monthly.orders.sum()):,}")
k2.metric("GMV", f"R$ {monthly.gross_merchandise_value.sum():,.0f}")
k3.metric("Unique customers", f"{int(monthly.customers.sum()):,}")
k4.metric("Average order value", f"R$ {monthly.average_order_value.mean():,.2f}")

left, right = st.columns(2)
with left:
    st.subheader("Monthly sales")
    fig = px.line(monthly, x="order_month", y="gross_merchandise_value", markers=True, labels={"order_month":"Month", "gross_merchandise_value":"GMV (R$)"})
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("Top product categories")
    st.plotly_chart(px.bar(categories, x="gmv", y="category", orientation="h", labels={"gmv":"GMV (R$)","category":"Category"}).update_layout(yaxis={"categoryorder":"total ascending"}), use_container_width=True)
left, right = st.columns(2)
with left:
    st.subheader("Sales by customer state")
    st.plotly_chart(px.bar(states.head(12), x="state", y="gmv", labels={"state":"State","gmv":"GMV (R$)"}), use_container_width=True)
with right:
    st.subheader("Delivery performance by status")
    st.dataframe(delivery, use_container_width=True, hide_index=True)
st.caption("GMV and average order value use order-item price and freight. Late delivery compares actual customer delivery with the estimated date.")

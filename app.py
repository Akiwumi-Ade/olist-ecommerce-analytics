"""Streamlit dashboard for the Olist PostgreSQL analytics model."""

from __future__ import annotations

import os
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()
st.set_page_config(page_title="Olist Commerce Analytics", page_icon="🛒", layout="wide")
st.title("Brazilian E-Commerce Analytics")
st.caption("Sales, delivery performance, and customer experience across the Olist marketplace")


@st.cache_resource
def engine_for(url: str):
    return create_engine(url, pool_pre_ping=True)


def query_df(engine, sql: str, params: dict | None = None) -> pd.DataFrame:
    return pd.read_sql_query(text(sql), engine, params=params or {})


url = os.getenv("DATABASE_URL")
if not url:
    st.error("Set DATABASE_URL in .env before launching the dashboard.")
    st.stop()
engine = engine_for(url)

try:
    bounds = query_df(
        engine,
        "SELECT min(order_month) AS first_month, max(order_month) AS last_month "
        "FROM analytics.monthly_sales",
    )
    if bounds.empty or pd.isna(bounds.loc[0, "first_month"]):
        st.info("No analytics data yet. Run the ETL pipeline first.")
        st.stop()

    first_month = pd.to_datetime(bounds.loc[0, "first_month"]).date()
    last_month = pd.to_datetime(bounds.loc[0, "last_month"]).date()
    st.sidebar.header("Filters")
    selected = st.sidebar.date_input(
        "Order month range",
        value=(first_month, last_month),
        min_value=first_month,
        max_value=last_month,
    )
    if isinstance(selected, tuple) and len(selected) == 2:
        start_date, end_date = selected
    elif isinstance(selected, date):
        start_date = end_date = selected
    else:
        st.info("Choose a start and end month to view the dashboard.")
        st.stop()

    # The date picker works at month grain; include the full selected end month.
    start_month = pd.Timestamp(start_date).replace(day=1)
    end_month_exclusive = pd.Timestamp(end_date).replace(day=1) + pd.offsets.MonthBegin(1)
    params = {"start_month": start_month, "end_month": end_month_exclusive}
    date_filter = "order_month >= :start_month AND order_month < :end_month"

    monthly = query_df(
        engine,
        f"SELECT * FROM analytics.monthly_sales WHERE {date_filter} ORDER BY order_month",
        params,
    )
    if monthly.empty:
        st.warning("No data in the selected month range.")
        st.stop()

    buyers = query_df(
        engine,
        f"""SELECT count(DISTINCT customer_unique_id) AS buyers
        FROM analytics.order_line_facts
        WHERE {date_filter} AND order_status NOT IN ('canceled', 'unavailable')""",
        params,
    )
    categories = query_df(
        engine,
        f"""SELECT category, sum(price) AS gmv
        FROM analytics.order_line_facts
        WHERE {date_filter} AND order_status NOT IN ('canceled', 'unavailable')
        GROUP BY category ORDER BY gmv DESC LIMIT 12""",
        params,
    )
    states = query_df(
        engine,
        f"""SELECT c.customer_state AS state, sum(f.price) AS gmv
        FROM analytics.order_line_facts f
        JOIN customers c USING (customer_id)
        WHERE {date_filter} AND f.order_status NOT IN ('canceled', 'unavailable')
        GROUP BY c.customer_state ORDER BY gmv DESC LIMIT 12""",
        params,
    )
    delivery = query_df(
        engine,
        """SELECT order_status,
            count(*) AS orders,
            avg(delivery_days) AS avg_delivery_days,
            100.0 * count(*) FILTER (WHERE is_late)
                / NULLIF(count(*) FILTER (WHERE order_estimated_delivery_date IS NOT NULL), 0) AS late_delivery_pct
        FROM analytics.order_facts
        WHERE order_purchase_timestamp >= :start_month
          AND order_purchase_timestamp < :end_month
          AND order_delivered_customer_date IS NOT NULL
        GROUP BY order_status ORDER BY orders DESC""",
        params,
    )
    review_delivery = query_df(
        engine,
        """SELECT review_score, count(*) AS orders,
            avg(delivery_days) AS avg_delivery_days,
            100.0 * count(*) FILTER (WHERE is_late)
                / NULLIF(count(*) FILTER (WHERE order_estimated_delivery_date IS NOT NULL), 0) AS late_delivery_pct
        FROM analytics.order_facts
        WHERE order_purchase_timestamp >= :start_month
          AND order_purchase_timestamp < :end_month
          AND order_delivered_customer_date IS NOT NULL
          AND review_score IS NOT NULL
        GROUP BY review_score ORDER BY review_score""",
        params,
    )
except SQLAlchemyError as exc:
    st.error(
        "The dashboard could not load its analytics. Check that PostgreSQL is running, "
        "DATABASE_URL is correct, and the ETL pipeline has completed."
    )
    with st.expander("Technical details"):
        st.code(str(exc.orig))
    st.stop()

st.sidebar.divider()
st.sidebar.caption(
    "GMV is item price before freight. Average order value includes item price and freight. "
    "Late delivery means delivery after the estimated date."
)

orders = int(monthly["orders"].sum())
gmv = float(monthly["gross_merchandise_value"].sum())
order_value = float(monthly["item_and_freight_value"].sum())
aov = order_value / orders if orders else 0
unique_buyers = int(buyers.loc[0, "buyers"])

k1, k2, k3, k4 = st.columns(4)
k1.metric("Orders", f"{orders:,}")
k2.metric("GMV", f"R$ {gmv:,.0f}")
k3.metric("Unique buyers", f"{unique_buyers:,}")
k4.metric("Average order value", f"R$ {aov:,.2f}")

left, right = st.columns(2)
with left:
    st.subheader("Monthly sales")
    fig = px.line(
        monthly,
        x="order_month",
        y="gross_merchandise_value",
        markers=True,
        labels={"order_month": "Month", "gross_merchandise_value": "GMV (R$)"},
    )
    st.plotly_chart(fig, width="stretch")
with right:
    st.subheader("Monthly orders")
    fig = px.bar(
        monthly,
        x="order_month",
        y="orders",
        labels={"order_month": "Month", "orders": "Orders"},
    )
    st.plotly_chart(fig, width="stretch")

left, right = st.columns(2)
with left:
    st.subheader("Top product categories")
    fig = px.bar(
        categories,
        x="gmv",
        y="category",
        orientation="h",
        labels={"gmv": "GMV (R$)", "category": "Category"},
    ).update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, width="stretch")
with right:
    st.subheader("Top customer states")
    fig = px.bar(
        states,
        x="gmv",
        y="state",
        orientation="h",
        labels={"gmv": "GMV (R$)", "state": "State"},
    ).update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, width="stretch")

left, right = st.columns(2)
with left:
    st.subheader("Delivery performance by order status")
    delivery = delivery.rename(
        columns={
            "order_status": "Order status",
            "orders": "Delivered orders",
            "avg_delivery_days": "Average delivery days",
            "late_delivery_pct": "Late delivery (%)",
        }
    )
    st.dataframe(delivery, width="stretch", hide_index=True)
with right:
    st.subheader("Delivery and review score")
    fig = px.bar(
        review_delivery,
        x="review_score",
        y="late_delivery_pct",
        hover_data={"orders": ":,", "avg_delivery_days": ":.1f"},
        labels={
            "review_score": "Average review score (1–5)",
            "late_delivery_pct": "Late delivery (%)",
        },
    )
    st.plotly_chart(fig, width="stretch")
st.caption(
    "All panels use the selected order-month range. GMV excludes freight; average order value "
    "includes freight and is weighted by order count. Buyer totals are distinct across the full range. "
    "Late delivery is measured among delivered orders with an estimated date; review scores are averaged per order."
)

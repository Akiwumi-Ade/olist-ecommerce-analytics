-- Rebuild in dependency order so view grain can evolve without CASCADE.
DROP VIEW IF EXISTS analytics.monthly_sales;
DROP VIEW IF EXISTS analytics.order_line_facts;
DROP VIEW IF EXISTS analytics.order_facts;

CREATE OR REPLACE VIEW analytics.order_facts AS
WITH item_totals AS (
    SELECT order_id,
           count(*) AS order_item_count,
           sum(price) AS gross_merchandise_value,
           sum(freight_value) AS freight_revenue
    FROM order_items
    GROUP BY order_id
),
payment_totals AS (
    SELECT order_id, sum(payment_value) AS order_payment_value
    FROM payments
    GROUP BY order_id
),
review_totals AS (
    SELECT order_id, avg(review_score)::numeric(3,1) AS review_score
    FROM reviews
    GROUP BY order_id
)
SELECT o.order_id, o.customer_id, c.customer_unique_id,
       o.order_status, o.order_purchase_timestamp,
       date_trunc('month', o.order_purchase_timestamp)::date AS order_month,
       o.order_delivered_customer_date, o.order_estimated_delivery_date,
       EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_purchase_timestamp)) / 86400.0
           AS delivery_days,
       (o.order_delivered_customer_date::date > o.order_estimated_delivery_date::date) AS is_late,
       COALESCE(i.order_item_count, 0) AS order_item_count,
       COALESCE(i.gross_merchandise_value, 0) AS gross_merchandise_value,
       COALESCE(i.freight_revenue, 0) AS freight_revenue,
       COALESCE(i.gross_merchandise_value, 0) + COALESCE(i.freight_revenue, 0)
           AS item_and_freight_value,
       COALESCE(p.order_payment_value, 0) AS order_payment_value,
       r.review_score
FROM orders o
JOIN customers c USING (customer_id)
LEFT JOIN item_totals i USING (order_id)
LEFT JOIN payment_totals p USING (order_id)
LEFT JOIN review_totals r USING (order_id);

CREATE OR REPLACE VIEW analytics.order_line_facts AS
SELECT o.order_id, oi.order_item_id, o.customer_id, c.customer_unique_id,
       o.order_status, o.order_purchase_timestamp,
       date_trunc('month', o.order_purchase_timestamp)::date AS order_month,
       o.order_delivered_customer_date, o.order_estimated_delivery_date,
       EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_purchase_timestamp)) / 86400.0
           AS delivery_days,
       (o.order_delivered_customer_date::date > o.order_estimated_delivery_date::date) AS is_late,
       oi.product_id, COALESCE(ct.product_category_name_english, p.product_category_name, 'Unknown') AS category,
       oi.seller_id, oi.price, oi.freight_value
FROM orders o
JOIN customers c USING (customer_id)
JOIN order_items oi USING (order_id)
JOIN products p USING (product_id)
LEFT JOIN category_translation ct USING (product_category_name);

CREATE OR REPLACE VIEW analytics.monthly_sales AS
SELECT order_month, count(*) AS orders,
       count(DISTINCT customer_unique_id) AS customers,
       sum(gross_merchandise_value) AS gross_merchandise_value,
       sum(freight_revenue) AS freight_revenue,
       sum(item_and_freight_value) AS item_and_freight_value,
       sum(item_and_freight_value) / NULLIF(count(*), 0) AS average_order_value
FROM analytics.order_facts
WHERE order_status NOT IN ('canceled', 'unavailable')
  AND order_item_count > 0
GROUP BY order_month;

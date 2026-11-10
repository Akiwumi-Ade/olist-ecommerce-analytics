CREATE OR REPLACE VIEW analytics.order_line_facts AS
SELECT o.order_id, oi.order_item_id, o.customer_id, c.customer_unique_id,
       o.order_status, o.order_purchase_timestamp,
       date_trunc('month', o.order_purchase_timestamp)::date AS order_month,
       o.order_delivered_customer_date, o.order_estimated_delivery_date,
       (o.order_delivered_customer_date::date - o.order_purchase_timestamp::date) AS delivery_days,
       (o.order_delivered_customer_date > o.order_estimated_delivery_date) AS is_late,
       oi.product_id, COALESCE(ct.product_category_name_english, p.product_category_name, 'Unknown') AS category,
       oi.seller_id, oi.price, oi.freight_value,
       COALESCE(pay.order_payment_value, 0) AS order_payment_value,
       rev.review_score
FROM orders o
JOIN customers c USING (customer_id)
JOIN order_items oi USING (order_id)
JOIN products p USING (product_id)
LEFT JOIN category_translation ct USING (product_category_name)
LEFT JOIN (SELECT order_id, sum(payment_value) AS order_payment_value FROM payments GROUP BY order_id) pay USING (order_id)
LEFT JOIN (SELECT order_id, avg(review_score)::numeric(3,2) AS review_score FROM reviews GROUP BY order_id) rev USING (order_id);

CREATE OR REPLACE VIEW analytics.monthly_sales AS
SELECT order_month, count(DISTINCT order_id) AS orders,
       count(DISTINCT customer_unique_id) AS customers,
       sum(price) AS gross_merchandise_value, sum(freight_value) AS freight_revenue,
       sum(price + freight_value) AS item_and_freight_value,
       sum(price + freight_value) / NULLIF(count(DISTINCT order_id), 0) AS average_order_value
FROM analytics.order_line_facts
WHERE order_status NOT IN ('canceled', 'unavailable')
GROUP BY order_month;

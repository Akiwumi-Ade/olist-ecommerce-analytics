CREATE SCHEMA IF NOT EXISTS analytics;
CREATE TABLE IF NOT EXISTS customers (
 customer_id text PRIMARY KEY, customer_unique_id text NOT NULL,
 customer_zip_code_prefix integer, customer_city text, customer_state text
);
CREATE TABLE IF NOT EXISTS sellers (
 seller_id text PRIMARY KEY, seller_zip_code_prefix integer, seller_city text, seller_state text
);
CREATE TABLE IF NOT EXISTS products (
 product_id text PRIMARY KEY, product_category_name text, product_name_lenght integer,
 product_description_lenght integer, product_photos_qty integer, product_weight_g numeric,
 product_length_cm numeric, product_height_cm numeric, product_width_cm numeric
);
CREATE TABLE IF NOT EXISTS category_translation (
 product_category_name text PRIMARY KEY, product_category_name_english text NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
 order_id text PRIMARY KEY, customer_id text NOT NULL REFERENCES customers(customer_id), order_status text NOT NULL,
 order_purchase_timestamp timestamp NOT NULL, order_approved_at timestamp,
 order_delivered_carrier_date timestamp, order_delivered_customer_date timestamp,
 order_estimated_delivery_date timestamp
);
CREATE TABLE IF NOT EXISTS order_items (
 order_id text NOT NULL REFERENCES orders(order_id), order_item_id integer NOT NULL,
 product_id text NOT NULL REFERENCES products(product_id), seller_id text NOT NULL REFERENCES sellers(seller_id),
 shipping_limit_date timestamp, price numeric(12,2) NOT NULL, freight_value numeric(12,2) NOT NULL,
 PRIMARY KEY(order_id, order_item_id)
);
CREATE TABLE IF NOT EXISTS payments (
 order_id text NOT NULL REFERENCES orders(order_id), payment_sequential integer NOT NULL,
 payment_type text NOT NULL, payment_installments integer NOT NULL, payment_value numeric(12,2) NOT NULL,
 PRIMARY KEY(order_id, payment_sequential)
);
CREATE TABLE IF NOT EXISTS reviews (
 review_id text NOT NULL, order_id text NOT NULL REFERENCES orders(order_id),
 review_score integer NOT NULL CHECK (review_score BETWEEN 1 AND 5),
 review_comment_title text, review_comment_message text, review_creation_date timestamp, review_answer_timestamp timestamp,
 PRIMARY KEY (review_id, order_id)
);
-- The public Olist data reuses review_id across different orders. Migrate older
-- project databases from the original single-column key before loading.
ALTER TABLE reviews DROP CONSTRAINT IF EXISTS reviews_pkey;
ALTER TABLE reviews ADD CONSTRAINT reviews_pkey PRIMARY KEY (review_id, order_id);
CREATE TABLE IF NOT EXISTS geolocation (
 geolocation_zip_code_prefix integer NOT NULL, geolocation_lat numeric(10,7), geolocation_lng numeric(10,7),
 geolocation_city text, geolocation_state text
);
CREATE INDEX IF NOT EXISTS idx_orders_purchase_ts ON orders(order_purchase_timestamp);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_items_product ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_items_seller ON order_items(seller_id);
CREATE INDEX IF NOT EXISTS idx_reviews_order ON reviews(order_id);
CREATE INDEX IF NOT EXISTS idx_geolocation_zip ON geolocation(geolocation_zip_code_prefix);

ALTER TABLE payments_clean
ADD CONSTRAINT pk_payments PRIMARY KEY (payment_id);

ALTER TABLE subscriptions_clean
ADD CONSTRAINT pk_subs PRIMARY KEY (subscription_id);

ALTER TABLE customers_clean
ADD CONSTRAINT pk_cust PRIMARY KEY (customer_id);

ALTER TABLE payments_clean
ADD CONSTRAINT fk_payments_subscription
FOREIGN KEY (subscription_id) REFERENCES subscriptions_clean (subscription_id);

ALTER TABLE subscriptions_clean
ADD CONSTRAINT fk_subscriptions_customers
FOREIGN KEY (customer_id) REFERENCES customers_clean (customer_id);
SELECT 
    MAX(CASE WHEN p.amount = 14.99 THEN p.payment_date END) AS last_old_price,
    MIN(CASE WHEN p.amount = 19.99 THEN p.payment_date END) AS first_new_price
FROM subscriptions_clean s
LEFT JOIN payments_clean p ON s.subscription_id = p.subscription_id
WHERE plan_type = 'Pro'
SELECT cus.customer_id, SUM(pay.amount) as total_s
FROM subscriptions_clean AS sub
JOIN customers_clean AS cus ON sub.customer_id = cus.customer_id
JOIN payments_clean AS pay ON sub.subscription_id = pay.subscription_id
GROUP BY cus.customer_id
ORDER BY total_s DESC
LIMIT 10
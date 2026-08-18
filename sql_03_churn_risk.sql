SELECT customer_id
FROM subscriptions_clean
GROUP BY customer_id
HAVING COUNT(*)=COUNT(end_date)
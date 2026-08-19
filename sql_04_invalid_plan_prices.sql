SELECT COUNT(*), plan_type, ROUND(AVG(p.amount)::numeric, 2), MIN(p.amount), MAX(p.amount)
FROM subscriptions_clean s
LEFT JOIN payments_clean p ON s.subscription_id = p.subscription_id
GROUP BY plan_type
SELECT * FROM
	(SELECT customers_clean.customer_id,
	ROW_NUMBER() OVER (PARTITION BY full_name, signup_date, city ORDER BY customer_id) as rnk
	FROM customers_clean
	WHERE is_valid_name = true) AS sub
WHERE sub.rnk !=1
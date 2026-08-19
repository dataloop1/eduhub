# 🎓 EduHub Subscription Analytics
Cleaning and validating data from an EdTech subscription service — from raw data to business insights.
![dashboard overview](images/powerbi_total.png)

## 📂About the data
The data has been synthetically generated and contains pre-defined issues.
It consists of three related tables:
```mermaid
erDiagram
    customers_clean ||--o{ subscriptions_clean : customer_id
    subscriptions_clean ||--o{ payments_clean : subscription_id
```
1 – Customers with names (where there was invalid data), signup date and their locations

![customers table](images/table_cust.png)

2 – A table of payments showing dates, subscription IDs and amounts

![payments table](images/table_pay.png)

3 – A table containing subscription details, including subscription type, start and end dates, and customer IDs

![subscriber table](images/table_subs.png)

I selected the analytical logic, methods for identifying incorrect data and working procedures myself; I was not aware of the specific issues present there

## 📋Task
A technical specification was drawn up with the following requirements:
- Data cleansing/validation (in Python)
- Data loading and validation in PostgreSQL
- Creation of a dashboard in Power BI that answered the following questions:
   - Seasonality of subscriptions
   - Number of active and closed subscriptions by plan
   - Number of invalid plans and users
   
## 🛠️Methods
### ![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white) Python
To begin with, the tables and their contents were checked to identify exactly what problems they contained.
After that, various methods were used depending on the specific issues.
For example:
- The case of the names was in itself an indicator of validity – if everything were converted to a single case, this indicator would be lost
```python
mask_blacklist_cus = customers_raw['full_name'].str.contains(r'\d')
pattern_cus = ~customers_raw['full_name'].str.contains(r'^[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+$', regex=True)
general_mask_customers = mask_blacklist_cus | pattern_cus
customers_raw['is_valid_name'] = np.where(general_mask_customers, False, True)
customers_raw['full_name'] = customers_raw['full_name'].str.strip()
```

- The city field does not contain any information regarding validity, so it was normalised

`customers_raw['city'] = customers_raw['city'].str.strip().str.lower()`

- To identify customers who had been recorded multiple times under different IDs, their name, registration date and city were used, as the issue in question was customers recorded multiple times under different IDs; if the ID had been included in the deduplication key, the result would have been zero
- Anti-join: first, subscriptions without a customer ID were identified, then payments without a subscription ID
```python
orphaned = subscriptions_raw[~subscriptions_raw['customer_id'].isin(customers_raw['customer_id'])]
subscriptions_raw = subscriptions_raw.drop(orphaned.index)
orph_rows = payments_raw[~payments_raw['subscription_id'].isin(subscriptions_raw['subscription_id'])]
payments_raw = payments_raw.drop(orph_rows.index)

```
This precisely reflects the structure of the tables themselves
customers -> subscriptions -> payments
- Typos in `plan_type` were found and corrected using value counts

### ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white) SQL

Following final validation, the cleaned-up tables were loaded back into the database.
Additional checks were carried out using PostgreSQL queries to verify the results.
Four invalid subscriptions were identified separately (see the next sub-section)
- Checking for duplicate lines
```sql
SELECT * FROM
	(SELECT customers_clean.customer_id,
	ROW_NUMBER() OVER (PARTITION BY full_name, signup_date, city ORDER BY customer_id) as rnk
	FROM customers_clean
	WHERE is_valid_name = true) AS sub
WHERE sub.rnk !=1
```
- JOIN all tables and top 10 users by amount
```sql
SELECT cus.customer_id, SUM(pay.amount) as total_s
FROM subscriptions_clean AS sub
JOIN customers_clean AS cus ON sub.customer_id = cus.customer_id
JOIN payments_clean AS pay ON sub.subscription_id = pay.subscription_id
GROUP BY cus.customer_id
ORDER BY total_s DESC
LIMIT 10
```
- Customers with no currently active subscription (churn risk)
```sql
SELECT customer_id
FROM subscriptions_clean
GROUP BY customer_id
HAVING COUNT(*)=COUNT(end_date)
```
### ![Power BI](https://img.shields.io/badge/Power_BI-F2C811?style=flat&logo=powerbi&logoColor=black) Power BI
Tables were imported into Power BI from the PostgreSQL database
- #### Invalid users and subscription invalid count
To count subscriptions with an invalid plan type, a measure was created using the 'valid_plans' column
```
Invalid Plan Count = CALCULATE(COUNTROWS('public subscriptions_clean'), 'public subscriptions_clean'[valid_plans] = FALSE())
```
To calculate the percentage of invalid users, the ‘is_valid_name’ column was used, divided by the total count (via COUNTROWS)
```
all_cus = COUNTROWS('public customers_clean')
invalid_cus = CALCULATE(COUNTA('public customers_clean'[is_valid_name]), 'public customers_clean'[is_valid_name] = FALSE())
```
```
% of invalid users = DIVIDE([invalid_cus], [all_cus])
```
- #### Active and closed subscriptions
- The absence of a date in the ‘end_date’ field indicates that a subscription is active. This was calculated using COUNTROWS + ISBLANK (for active subscriptions) and COUNTROWS + NOT ISBLANK (for closed subscriptions) 
```
Active subscriptions = CALCULATE(COUNTROWS('public subscriptions_clean'), ISBLANK('public subscriptions_clean'[end_date]))
```
```
Closed subscriptions = CALCULATE(COUNTROWS('public subscriptions_clean'), NOT(ISBLANK('public subscriptions_clean'[end_date])))
```
- #### New subscriptions by date
 To do this, I needed to create a helper ‘calendar’ table 
```
Calendar = CALENDAR(
    MIN(
        MIN('public subscriptions_clean'[start_date]),
        MIN(
            MIN('public subscriptions_clean'[end_date]),
            MIN(
                MIN('public customers_clean'[signup_date]),
                MIN('public payments_clean'[payment_date])
            )
        )
    ),
    MAX(
        MAX('public subscriptions_clean'[start_date]),
        MAX(
            MAX('public subscriptions_clean'[end_date]),
            MAX(
                MAX('public customers_clean'[signup_date]),
                MAX('public payments_clean'[payment_date])
            )
        )
    )
)
```
In addition, three extra columns were extracted from 
the calendar: day, month and year, plus a helper ‘MonthNo’ column to sort the months by calendar rather than alphabetically
```
Day = DAY('Calendar'[Date])
Month = FORMAT('Calendar'[Date], "MMMM", "en-US")
MonthNo = MONTH('Calendar'[Date])
Year = YEAR('Calendar'[Date])
```

## 🔎Data quality
During the audit, using SQL queries, four records were identified which I initially decided to exclude from the dashboard.
- There was a range of prices for the Pro plan
- These four subscriptions generate 56 payments in total (32 for the blank value, 24 for 'Standart'), all priced at $14.99

A hypothesis arose that the price for the Pro plan had changed at some point

As a result of the query
```sql
SELECT COUNT(*), plan_type, ROUND(AVG(p.amount)::numeric, 2), MIN(p.amount), MAX(p.amount)
FROM subscriptions_clean s
LEFT JOIN payments_clean p ON s.subscription_id = p.subscription_id
GROUP BY plan_type
```
| count | plan_type | round | min   | max   |
|-------|-----------|-------|-------|-------|
| 32    | [null]    | 14.99 | 14.99 | 14.99 |
| 1262  | Basic     | 10.24 | 9.99  | 14.99 |
| 1371  | Pro       | 19.58 | 14.99 | 19.99 |
| 1628  | Premium   | 29.89 | 14.99 | 29.99 |
| 24    | Standart  | 14.99 | 14.99 | 14.99 |

```sql
SELECT 
    MAX(CASE WHEN p.amount = 14.99 THEN p.payment_date END) AS last_old_price,
    MIN(CASE WHEN p.amount = 19.99 THEN p.payment_date END) AS first_new_price
FROM subscriptions_clean s
LEFT JOIN payments_clean p ON s.subscription_id = p.subscription_id
WHERE plan_type = 'Pro'
```
| last_old_price      | first_new_price     | 
|---------------------|---------------------|
| 2026-05-01 00:00:00 | 2022-01-08 00:00:00 | 
it was found that both prices existed throughout the entire period (14.99 appears from April 2022 to May 2026, 19.99 from January 2022), rather than replacing one another – the hypothesis was not confirmed.

Final decision – mark these four entries as ‘False’ in `valid_plans`; do not delete them without good reason

## 💼Insights & Business Impact


### Subscription Retention by Plan
- **Insight:** The proportion of active subscriptions decreases from Premium to Basic (from 42% to 31%)
- **Recommendation:** Warrants further investigation into retention drivers; suggest that Basic customers switch to advanced tariffs

### Seasonality
- **Insight:** No consistent upward trend was identified across any particular months; the pattern is erratic (for example, February: 3→11→11→4). The only consistent trend is the year-on-year increase in the total number of subscriptions
- **Recommendation:** There is no need to plan around anticipated peak months. It is preferable to factor in growth along the overall trajectory

### Data Quality (Invalid Users)
- **Insight:** 15 out of 312 customers have an incorrectly recorded name, plus 4 subscriptions with an unspecified plan type
- **Recommendation:** 15 out of 312 is a large number for manual correction. It is recommended that name validation be implemented at the data entry stage to prevent the problem from accumulating further

## 💻How to Run / Limitations
- The `.env` file with database credentials is not included in the repository for security reasons, so it is not possible to reproduce the pipeline from scratch without local PostgreSQL setup
- The `.pbix` file opens with a full data snapshot already embedded, so no database access is needed to view it
- Clicking "Refresh" will require valid PostgreSQL credentials and will show an authentication error otherwise

## 👾Technologies
- ![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white) Python (Pandas, NumPy, SQLAlchemy, python-dotenv)
- ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white) PostgreSQL
- ![Power BI](https://img.shields.io/badge/Power_BI-F2C811?style=flat&logo=powerbi&logoColor=black) Power BI (Power Query, DAX)
- ![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat&logo=github&logoColor=white) Git/GitHub
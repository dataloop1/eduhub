from sqlalchemy import create_engine
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_engine(f'postgresql+psycopg2://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}')

customers_raw =  pd.read_sql('SELECT * FROM customers_raw', engine)
payments_raw = pd.read_sql('SELECT * FROM payments_raw', engine)
subscriptions_raw = pd.read_sql('SELECT * FROM subscriptions_raw', engine)

customers_raw['signup_date'] = pd.to_datetime(customers_raw['signup_date'])
customers_raw['city'] = customers_raw['city'].str.strip().str.lower()

mask_blacklist_cus = customers_raw['full_name'].str.contains(r'\d')
pattern_cus = ~customers_raw['full_name'].str.contains(r'^[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+$', regex=True)
general_mask_customers = mask_blacklist_cus | pattern_cus
customers_raw['is_valid_name'] = np.where(general_mask_customers, False, True)
customers_raw['full_name'] = customers_raw['full_name'].str.strip()

customers_raw = customers_raw.drop_duplicates(subset=['signup_date', 'full_name', 'city'])

plans = ['Premium', 'Basic', 'Pro']
subscriptions_raw['plan_type'] = subscriptions_raw['plan_type'].str.capitalize()
subscriptions_raw['plan_type'] = subscriptions_raw['plan_type'].replace({'Baisc': 'Basic', 'Premuim': 'Premium'})
mask_plans = subscriptions_raw['plan_type'].isin(plans)
subscriptions_raw['valid_plans'] = np.where(mask_plans, True, False)

subscriptions_raw['start_date'] = pd.to_datetime(subscriptions_raw['start_date'])
subscriptions_raw['end_date'] = pd.to_datetime(subscriptions_raw['end_date'])

orphaned = subscriptions_raw[~subscriptions_raw['customer_id'].isin(customers_raw['customer_id'])]
subscriptions_raw = subscriptions_raw.drop(orphaned.index)

orph_rows = payments_raw[~payments_raw['subscription_id'].isin(subscriptions_raw['subscription_id'])]
payments_raw = payments_raw.drop(orph_rows.index)

payments_raw['amount'] =payments_raw['amount'].str.strip().str.replace(' ', '').str.replace(',', '.')
payments_raw['amount'] = pd.to_numeric(payments_raw['amount'], errors='coerce')

payments_raw['payment_date'] = pd.to_datetime(payments_raw['payment_date'], errors='coerce')

data_to_export = {
    'customers_clean': customers_raw,
    'subscriptions_clean': subscriptions_raw,
    'payments_clean': payments_raw
}
for table_name, df in data_to_export.items():
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists='replace',
        index=False
    )
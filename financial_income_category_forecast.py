# financial_income_category_forecast.py
# FULL AI: Income + Expense + Category-Level Forecasting (All Horizons)
# FIXED: UnicodeEncodeError → Uses only ASCII-safe characters

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from prophet import Prophet
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
import warnings
import os
import sqlite3
import requests
from datetime import datetime

# -------------------------------
# FORCE UTF-8 OUTPUT (Windows fix)
# -------------------------------
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

warnings.filterwarnings("ignore")
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

# ----------------------------
# CONFIG — NOW USING DATABASE
# ----------------------------
DB_FILE = "finance.db"           # Your new database
TABLE_NAME = "transactions"      # Change if your table has different name
OUTPUT_DIR = "income_expense_forecast"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Horizons
HORIZONS = [
    ("4 Days", 4, 'D'),
    ("4 Weeks", 4, 'W'),
    ("2 Months", 2, 'M'),
    ("4 Months", 4, 'M'),
    ("1 Year", 12, 'M')
]

print("ULTIMATE AI FINANCIAL ENGINE — Powered by finance.db")
print("="*80)

# ----------------------------
# 1. Load from SQLite Database
# ----------------------------
print(f"Connecting to database: {DB_FILE}...")
try:
    conn = sqlite3.connect(DB_FILE)
    query = f"SELECT * FROM {TABLE_NAME}"
    df = pd.read_sql_query(query, conn)
    conn.close()
    print(f"Loaded {len(df):,} transactions from database")
except Exception as e:
    raise ConnectionError(f"Cannot connect to {DB_FILE}: {e}")

# Drop unnamed columns
df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

# Replace NULL
df = df.replace(['NULL', 'null', ''], np.nan)

# Required columns (adjust if your DB uses different names)
required = ['date', 'title', 'category', 'account', 'amount', 'currency', 'type']
missing = [col for col in required if col not in df.columns]
if missing:
    raise ValueError(f"Missing columns in database: {missing}")

# Parse date
df['Date'] = pd.to_datetime(df['date'], errors='coerce')
df = df.dropna(subset=['Date'])

# Parse amount
df['Amount'] = pd.to_numeric(df['amount'], errors='coerce')
df = df.dropna(subset=['Amount'])

# Parse type
df['Type'] = df['type'].astype(str).str.strip().str.upper()
df = df[df['Type'].isin(['INCOME', 'EXPENSE'])]

# Optional columns
df['is_recurring'] = pd.to_numeric(df.get('is_recurring', 0), errors='coerce').fillna(0).astype(int)
df['interval'] = df.get('interval', '').astype(str).str.strip().str.lower().fillna('')

# Clean column names
df = df.rename(columns={
    'title': 'Title',
    'category': 'Category',
    'account': 'Account',
    'currency': 'Currency'
})

# ----------------------------
# 2. Shared Currency Configuration 
# ----------------------------
# Define supported currencies (same as Streamlit)
currency_options = [
    "MYR", "USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "CNY", "SEK",
    "NZD", "KRW", "SGD", "NOK", "MXN", "BRL", "ZAR", "RUB", "TRY", "AED",
    "INR", "PHP", "IDR", "THB", "VND", "PKR", "BDT", "LKR", "MMK", "EGP"
]

# Optional: symbol map (not used in forecasting, but kept for consistency)
currency_symbol_map = {
    "MYR": "RM", "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
    "INR": "₹", "SGD": "S$", "AUD": "A$", "CAD": "C$", "CHF": "Fr",
    "CNY": "¥", "KRW": "₩", "AED": "د.إ", "THB": "฿", "IDR": "Rp",
    "PHP": "₱", "ZAR": "R", "BRL": "R$", "MXN": "$", "TRY": "₺",
    "SEK": "kr", "NOK": "kr", "NZD": "NZ$"
}

def get_exchange_rate(base="MYR", target="MYR"):
    """Get exchange rate using the same logic as Streamlit (without Streamlit dependency)."""
    if base == target:
        return 1.0
    try:
        import requests
        url = f"https://api.exchangerate-api.com/v4/latest/{base}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['rates'].get(target, 1.0)
    except Exception as e:
        print(f"⚠️ Exchange rate API error: {e}. Using fallback rate = 1.0.")
    return 1.0

# Determine target currency (from environment or default to MYR)
import os
TARGET_CURRENCY = os.getenv("FORECAST_CURRENCY", "MYR")

# Validate currency
if TARGET_CURRENCY not in currency_options:
    print(f"⚠️ Warning: '{TARGET_CURRENCY}' is not in supported currencies. Using MYR.")
    TARGET_CURRENCY = "MYR"

# Apply currency conversion if needed
if TARGET_CURRENCY != "MYR":
    print(f"🌍 Converting transaction amounts from MYR to {TARGET_CURRENCY}...")
    EXCHANGE_RATE = get_exchange_rate("MYR", TARGET_CURRENCY)
    df['Amount'] = df['Amount'] * EXCHANGE_RATE
    print(f"✅ Applied exchange rate: 1 MYR = {EXCHANGE_RATE:.4f} {TARGET_CURRENCY}")
else:
    EXCHANGE_RATE = 1.0
    print("📊 Using base currency: MYR")

# Proceed with income/expense split (unchanged)
df_income = df[df['Type'] == 'INCOME'].copy()
df_expense = df[df['Type'] == 'EXPENSE'].copy()

# Day of week
df['DayOfWeek'] = df['Date'].dt.dayofweek

# Clean categories
df_income['Category'] = df_income['Category'].astype(str).str.strip().str.title()
df_expense['Category'] = df_expense['Category'].astype(str).str.strip().str.title()

print(f"Income rows: {len(df_income):,}")
print(f"Expense rows: {len(df_expense):,}")
print(f"Date range: {df['Date'].min().date()} → {df['Date'].max().date()}")
print(f"Income sources: {sorted(df_income['Category'].unique())}")
print(f"Expense categories: {sorted(df_expense['Category'].unique())}")

# ----------------------------
# 3. Aggregate by Frequency
# ----------------------------
def aggregate_by_freq(data, freq, value_col='Amount'):
    agg = data.copy()
    agg['Period'] = agg['Date'].dt.to_period(freq).dt.to_timestamp()
    grouped = agg.groupby(['Period', 'Category'])[value_col].sum().unstack(fill_value=0)
    grouped = grouped.reset_index()
    return grouped

# ----------------------------
# 4. Forecast Series
# ----------------------------
def forecast_series(data, col, name, periods, freq, horizon_label, kind=""):
    df_p = data[['Period', col]].copy()
    df_p.columns = ['ds', 'y']
    df_p = df_p.dropna().sort_values('ds')
    if len(df_p) < 3:
        return None

    model = Prophet(
        yearly_seasonality=(freq in ['D', 'W']),
        weekly_seasonality=(freq == 'D'),
        daily_seasonality=False,
        seasonality_mode='additive',
        interval_width=0.8
    )
    model.fit(df_p)

    future = model.make_future_dataframe(periods=periods, freq=freq)
    forecast = model.predict(future)

    # Plot
    fig = model.plot(forecast)
    plt.title(f"{kind} {name} - {horizon_label}")
    plt.ylabel(TARGET_CURRENCY)  # Updated Y-label
    safe_name = "".join(c for c in name if c.isalnum() or c in " _-")
    safe_h = horizon_label.replace(" ", "_")
    cur_suffix = f"_{TARGET_CURRENCY}" if TARGET_CURRENCY != "MYR" else ""
    plt.savefig(f"{OUTPUT_DIR}/{safe_h}_{kind.lower()}_{safe_name}_forecast{cur_suffix}.png",
                dpi=300, bbox_inches='tight')
    plt.close()

    pred = forecast[['ds', 'yhat']].tail(periods).copy()
    fmt = '%Y-%m-%d' if freq in ['D', 'W'] else '%Y-%m'
    pred['ds'] = pred['ds'].dt.strftime(fmt)
    return pred.round(2)

# ----------------------------
# 5. INCOME FORECASTING
# ----------------------------
print("\nForecasting INCOME (overall + by source)...")
income_categories = df_income['Category'].unique()

for label, periods, freq in HORIZONS:
    print(f"  -> {label}")
    agg_income = aggregate_by_freq(df_income, freq)
    agg_income['Total_Income'] = agg_income[income_categories].sum(axis=1)

    # Total
    total_forecast = forecast_series(agg_income, 'Total_Income', 'Total Income', periods, freq, label, kind="Income")

    # Per source
    source_forecasts = []
    for cat in income_categories:
        print(f"     - {cat}")  # ASCII-safe
        f = forecast_series(agg_income, cat, cat, periods, freq, label, kind="Income")
        if f is not None:
            f['Source'] = cat
            source_forecasts.append(f)

    if total_forecast is not None and source_forecasts:
        safe_label = label.replace(" ", "_")
        cur_suffix = f"_{TARGET_CURRENCY}" if TARGET_CURRENCY != "MYR" else ""
        total_path = f"{OUTPUT_DIR}/{safe_label}_TOTAL_INCOME{cur_suffix}.csv"
        total_forecast.rename(columns={'ds': 'Date', 'yhat': 'Predicted_Income'}).to_csv(total_path, index=False)

        combined = pd.concat(source_forecasts, ignore_index=True)
        combined = combined[['ds', 'Source', 'yhat']].rename(columns={'ds': 'Date', 'yhat': 'Predicted_Income'})
        src_path = f"{OUTPUT_DIR}/{safe_label}_INCOME_BY_SOURCE{cur_suffix}.csv"
        combined.to_csv(src_path, index=False)

# ----------------------------
# 6. EXPENSE FORECASTING
# ----------------------------
print("\nForecasting EXPENSE by category...")
expense_categories = df_expense['Category'].unique()

for label, periods, freq in HORIZONS:
    print(f"  -> {label}")
    agg_expense = aggregate_by_freq(df_expense, freq)

    forecasts = []
    for cat in expense_categories:
        print(f"     - {cat}")  # ASCII-safe
        f = forecast_series(agg_expense, cat, cat, periods, freq, label, kind="Expense")
        if f is not None:
            f['Category'] = cat
            forecasts.append(f)

    if forecasts:
        combined = pd.concat(forecasts, ignore_index=True)
        combined = combined[['ds', 'Category', 'yhat']].rename(columns={'ds': 'Date', 'yhat': 'Predicted_Spending'})
        safe_label = label.replace(" ", "_")
        cur_suffix = f"_{TARGET_CURRENCY}" if TARGET_CURRENCY != "MYR" else ""
        path = f"{OUTPUT_DIR}/{safe_label}_EXPENSE_BY_CATEGORY{cur_suffix}.csv"
        combined.to_csv(path, index=False)

# ----------------------------
# 7. NET BALANCE
# ----------------------------
print("\nForecasting NET BALANCE (6 months)...")
monthly_income = df_income.groupby(df_income['Date'].dt.to_period('M').dt.to_timestamp())['Amount'].sum().reset_index()
monthly_expense = df_expense.groupby(df_expense['Date'].dt.to_period('M').dt.to_timestamp())['Amount'].sum().reset_index()

monthly = pd.merge(monthly_income, monthly_expense, on='Date', how='outer', suffixes=('_Income', '_Expense')).fillna(0)
monthly['Net'] = monthly['Amount_Income'] - monthly['Amount_Expense']

df_net = monthly[['Date', 'Net']].copy()
df_net.columns = ['ds', 'y']

if len(df_net) >= 3:
    model_net = Prophet(yearly_seasonality=True)
    model_net.fit(df_net)
    future_net = model_net.make_future_dataframe(periods=6, freq='M')
    forecast_net = model_net.predict(future_net)[['ds', 'yhat']].tail(6)
    forecast_net['ds'] = forecast_net['ds'].dt.strftime('%Y-%m')
    forecast_net = forecast_net.round(2).rename(columns={'ds': 'Month', 'yhat': 'Predicted_Net'})
else:
    forecast_net = pd.DataFrame({'Month': [], 'Predicted_Net': []})

cur_suffix = f"_{TARGET_CURRENCY}" if TARGET_CURRENCY != "MYR" else ""
net_path = f"{OUTPUT_DIR}/NET_BALANCE_6_MONTHS{cur_suffix}.csv"
forecast_net.to_csv(net_path, index=False)

# ----------------------------
# 8. ML Predictions
# ----------------------------
print("\nTraining next-transaction models...")
X_amt = pd.get_dummies(df[['Category', 'Account', 'DayOfWeek']], columns=['Category', 'Account'], drop_first=True)
y_amt = df['Amount']
X_train, X_test, y_train, y_test = train_test_split(X_amt, y_amt, test_size=0.2, random_state=42)
rf = RandomForestRegressor(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)
mae = mean_absolute_error(y_test, rf.predict(X_test))

X_cat = pd.get_dummies(df[['Amount', 'Account', 'DayOfWeek']], columns=['Account'], drop_first=True)
y_cat = df['Category']
le = LabelEncoder()
y_cat_encoded = le.fit_transform(y_cat)
xgb = XGBClassifier(random_state=42, eval_metric='mlogloss')
xgb.fit(X_cat, y_cat_encoded)
pred_cat_encoded = xgb.predict(X_cat.iloc[-1:].copy())[0]
pred_cat = le.inverse_transform([pred_cat_encoded])[0]

# ----------------------------
# 9. Final Report
# ----------------------------
report = f"""
# Full Financial AI Report — {TARGET_CURRENCY}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Base Currency:** MYR → **Forecast Currency:** {TARGET_CURRENCY}
**Exchange Rate Used:** 1 MYR = {EXCHANGE_RATE:.4f} {TARGET_CURRENCY}

## Summary
- Income entries: {len(df_income):,}
- Expense entries: {len(df_expense):,}
- Date range: {df['Date'].min().date()} to {df['Date'].max().date()}
- Forecast currency: **{TARGET_CURRENCY}**

## Forecasts
"""
for h in HORIZONS:
    report += f"- {h[0]}\n"

report += f"""
## 6-Month Net
{forecast_net.to_markdown(index=False) if not forecast_net.empty else "Not enough data"}

## Predictions
- Next amount MAE: {mae:.2f} {TARGET_CURRENCY}
- Next category: **{pred_cat}**

> Saved in `./{OUTPUT_DIR}/`
"""

with open(f"{OUTPUT_DIR}/FULL_FINANCIAL_REPORT_{TARGET_CURRENCY}.md", "w", encoding='utf-8') as f:
    f.write(report.strip())

print(f"\nReport: {OUTPUT_DIR}/FULL_FINANCIAL_REPORT_{TARGET_CURRENCY}.md")
print(f"Charts & CSVs: ./{OUTPUT_DIR}/")
print("\nDone! AI Forecasting Complete.")

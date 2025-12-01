# pages/add_transaction.py
import streamlit as st
import pandas as pd
import uuid
from datetime import datetime, date, time, timedelta
from dateutil.relativedelta import relativedelta
from database import init_db, add_transaction, get_last_n, format_display_df
from datetime import datetime, date, time, timedelta, timezone
import requests
import os

# -------------------------------
# Exchange Rate Helper
# -------------------------------
def convert_to_myr(amount: float, from_currency: str) -> float:
    """Convert amount from 'from_currency' to MYR using live exchange rate."""
    if from_currency == "MYR":
        return amount
    try:
        # Fetch: 1 [from_currency] = ? MYR
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            myr_rate = data['rates'].get('MYR')
            if myr_rate is not None:
                return amount * myr_rate
        return amount  # fallback to original if API fails
    except Exception as e:
        st.warning(f"⚠️ Could not convert {from_currency} to MYR. Storing as-is.")
        return amount

# -------------------------------
# Ensure login
# -------------------------------
if not st.session_state.get("logged_in"):
    st.error("Please log in first.")
    if st.button("Go to Login"):
        st.session_state.clear()
        st.switch_page("app.py")
    st.stop()

# -------------------------------
# Page Configuration
# -------------------------------
st.set_page_config(
    page_title="Add Transaction",
    page_icon="logo_circle.png",
    layout="wide"
)

# -------------------------------
# Sidebar – Only Logout
# -------------------------------
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.switch_page("app.py")

# -------------------------------
# Custom CSS (Pink Theme + Clean Back Button)
# -------------------------------
st.markdown("""
    <style>
    .stApp {
        background-color: white !important;
        margin-top: -30px; 
    }
    .main {
        background-color: white !important;
        padding: 20px;
        font-family: 'Segoe UI', sans-serif;
        margin-top: -20px; 
    }
    .stButton>button:not(.back-button) {
        background: linear-gradient(145deg, #ec407a, #d81b60);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 12px;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(216,27,96,0.3);
        width: 100%;
    }
    .stButton>button:not(.back-button):hover {
        transform: translateY(-2px);
    }
    .stSidebar .stButton > button {
        background: white !important;
        color: #333 !important;
        border: 1px solid #ddd !important;
        box-shadow: none !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        font-weight: normal !important;
        width: auto !important;
        transform: none !important;
    }
    .stSidebar .stButton > button:hover {
        background: #f8f8f8 !important;
        border-color: #ccc !important;
    }
    .back-button {
        background: none !important;
        border: none !important;
        padding: 0 !important;
        color: #d81b60 !important;
        font-weight: 600 !important;
        text-align: left !important;
        width: auto !important;
        box-shadow: none !important;
        transform: none !important;
        cursor: pointer !important;
    }
    .back-button:hover {
        text-decoration: underline !important;
        color: #c2185b !important;
    }
    h1 {
        color: #d81b60;
        text-align: center;
        font-weight: 600;
    }
    .success-msg {
    background: #e8f5e9 !important;
    color: #2e7d32 !important;
    padding: 14px 20px !important;
    border-radius: 16px !important;
    font-weight: 600 !important;
    font-size: 1.05em !important;
    white-space: nowrap !important;        
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    max-width: 100% !important;
    box-shadow: 0 4px 12px rgba(46, 125, 50, 0.15) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# -------------------------------
# Header
# -------------------------------
header_container = st.container()
with header_container:
    col_back, col_title, col_spacer = st.columns([0.5, 4, 0.5])
    with col_back:
        if st.button("←", key="back_to_dashboard", help="Return to Dashboard"):
            keys_to_clear = ["is_income", "is_recurring", "recurring_inter", "recurring_end_date"]
            for k in keys_to_clear:
                if k in st.session_state:
                    del st.session_state[k]
            st.switch_page("pages/dashboard.py")
    
    with col_title:
        st.markdown(
            "<h1 style='text-align:center; color: black; font-weight:700; font-size:2.6em; margin-bottom:8px;'>"
            "➕ Add New Transaction"
            "</h1>"
            "<p style='text-align:center; color:#ec407a; font-size:1.1em; margin-top:-10px;'>"
            "Track your income and expenses effortlessly"
            "</p>",
            unsafe_allow_html=True
        )
    with col_spacer:
        st.write("")

# -------------------------------
# Reactive State Initialization
# -------------------------------
if 'is_income' not in st.session_state:
    st.session_state.is_income = False
if 'is_recurring' not in st.session_state:
    st.session_state.is_recurring = False
if 'recurring_inter' not in st.session_state:
    st.session_state.recurring_inter = "Monthly"
if 'recurring_end_date' not in st.session_state:
    st.session_state.recurring_end_date = None

# -------------------------------
# Income vs Expense Toggle
# -------------------------------
st.markdown("### 💰 Type")
col1, col2 = st.columns(2)
with col1:
    if st.button("💸 Expense", key="expense", use_container_width=True):
        st.session_state.is_income = False
with col2:
    if st.button("📈 Income", key="income", use_container_width=True):
        st.session_state.is_income = True

trans_type = "Income" if st.session_state.is_income else "Expense"
color = "#4caf50" if st.session_state.is_income else "#f44336"
st.markdown(f"<p style='text-align:center; font-weight:600; color:{color};'>Selected: <strong>{trans_type}</strong></p>", unsafe_allow_html=True)

# -------------------------------
# Form Inputs
# -------------------------------
st.markdown("### 📝 Details")

name = st.text_input("Name", placeholder="e.g., Juice, Salary")

amount_str = st.text_input(
    "Amount",
    placeholder="e.g., 1500.00 or 1,234.56",
    help="Enter any positive number. Commas allowed."
)

categories = [
    "Bills", "Education", "Entertainment", "Family", "Food", 
    "Grocery", "Health", "Insurance", "Other", "Transport", "Travel"
]
category = st.selectbox("Category", [""] + categories, index=0)

accounts = ["Savings Bank", "Salary Bank", "Cash", "Credit Card", "Wallet"]
account = st.selectbox("Account", accounts, index=2)

currency_options = [
    "MYR", "USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "CNY", "SEK",
    "NZD", "KRW", "SGD", "NOK", "MXN", "BRL", "ZAR", "RUB", "TRY", "AED",
    "INR", "PHP", "IDR", "THB", "VND", "PKR", "BDT", "LKR", "MMK", "EGP"
]
currency = st.selectbox("Currency", currency_options, index=currency_options.index("MYR"))

st.markdown("### 📅 Date & Time")
col_date, col_time = st.columns(2)
with col_date:
    trans_date = st.date_input("Date", value=date.today())

with col_time:
    malaysia_time = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
    current_time = malaysia_time.strftime("%H:%M")
    time_input = st.text_input(
        "Time",
        value=current_time,
        max_chars=5,
        help="Malaysia time (UTC+8)"
    )
    try:
        trans_time = datetime.strptime(time_input.strip(), "%H:%M").time()
    except:
        trans_time = malaysia_time.time()

trans_datetime = datetime.combine(trans_date, trans_time)

# -------------------------------
# RECURRING TOGGLE + END DATE
# -------------------------------
st.markdown("### 🔁 Recurring?")

is_recurring = st.checkbox(
    "Is this a recurring transaction?",
    value=st.session_state.is_recurring,
    key="recurring_checkbox"
)
st.session_state.is_recurring = is_recurring

if st.session_state.is_recurring:
    inter_options = ["Daily", "Weekly", "Monthly", "Yearly"]
    selected_inter = st.selectbox(
        "Frequency",
        inter_options,
        index=inter_options.index(st.session_state.recurring_inter),
        key="recurring_inter_select"
    )
    st.session_state.recurring_inter = selected_inter

    st.markdown("#### End Date (Optional)")
    end_date_input = st.date_input(
        "Stop recurring after",
        value=None,
        min_value=trans_date + timedelta(days=1),
        help="Leave blank to continue for 1 year",
        key="recurring_end_date_input"
    )
    st.session_state.recurring_end_date = end_date_input

    max_end = end_date_input if end_date_input else (trans_date + timedelta(days=365))
    delta_days = (max_end - trans_date).days

    if selected_inter == "Daily":
        count = min(delta_days + 1, 365)
    elif selected_inter == "Weekly":
        count = min((delta_days // 7) + 1, 52)
    elif selected_inter == "Monthly":
        count = min(((max_end.year - trans_date.year) * 12 + max_end.month - trans_date.month) + 1, 12)
    else:
        count = min(max_end.year - trans_date.year + 1, 1)

    st.info(f"Will create **{count}** entries until **{max_end.strftime('%Y-%m-%d')}**.")

# -------------------------------
# DATABASE: Init
# -------------------------------
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# -------------------------------
# Submit Button & Save
# -------------------------------
if st.button("✅ Add Record", type="primary"):
    if not name.strip():
        st.error("⚠️ Please enter a Name.")
        st.stop()
    if not amount_str.strip():
        st.error("⚠️ Please enter an Amount.")
        st.stop()
    
    try:
        raw_amount = float(amount_str.replace(",", "").strip())
        if raw_amount <= 0:
            st.error("⚠️ Amount must be greater than 0.")
            st.stop()
    except ValueError:
        st.error("⚠️ Please enter a valid number (e.g., 1500 or 1,234.56).")
        st.stop()

    if not category:
        st.error("⚠️ Please select a Category.")
        st.stop()

    # ✅ Convert user-input amount to MYR for storage
    amount_in_myr = convert_to_myr(raw_amount, currency)

    record_type = "INCOME" if st.session_state.is_income else "EXPENSE"
    base_datetime = trans_datetime
    entries_to_add = []

    if st.session_state.is_recurring:
        interval = st.session_state.recurring_inter
        end_date = st.session_state.recurring_end_date
        max_end = end_date if end_date else (trans_datetime.date() + timedelta(days=365))

        current_dt = trans_datetime
        while current_dt.date() <= max_end:
            entries_to_add.append({
                "id": str(uuid.uuid4()),
                "date": current_dt,
                "title": name.strip(),
                "category": category,
                "account": account,
                "amount": amount_in_myr,      # ← STORED IN MYR
                "currency": currency,         # ← ORIGINAL CURRENCY (for display/edit)
                "type": record_type,
                "is_recurring": 1,
                "interval": interval.lower()
            })

            if interval == "Daily":
                current_dt += timedelta(days=1)
            elif interval == "Weekly":
                current_dt += timedelta(weeks=1)
            elif interval == "Monthly":
                current_dt += relativedelta(months=1)
            else:
                current_dt += relativedelta(years=1)
    else:
        entries_to_add.append({
            "id": str(uuid.uuid4()),
            "date": base_datetime,
            "title": name.strip(),
            "category": category,
            "account": account,
            "amount": amount_in_myr,      # ← STORED IN MYR
            "currency": currency,         # ← ORIGINAL CURRENCY
            "type": record_type,
            "is_recurring": 0,
            "interval": None
        })

    try:
        for entry in entries_to_add:
            add_transaction(entry)

        st.success(
            f"✅ Saved **{len(entries_to_add)}** transaction(s): "
            f"**{name.strip()}** → {raw_amount:,.2f} {currency} ({record_type})"
        )
        # THIS IS THE NUCLEAR FIX — FORCES INSTANT REFRESH EVERYWHERE
        st.cache_data.clear()                     # Clears ALL Streamlit cache
        st.session_state.new_transaction_added = True     

        # Reset form
        st.session_state.is_income = False
        st.session_state.is_recurring = False
        st.session_state.recurring_inter = "Monthly"
        st.session_state.recurring_end_date = None

    except Exception as e:
        st.error(f"Database error: {e}")

# -------------------------------
# Show Last 5 Entries 
# -------------------------------
if st.checkbox("Show last 5 entries"):
    df_raw = get_last_n(5)
    if not df_raw.empty:
        df_disp = format_display_df(df_raw)
        st.dataframe(
            df_disp[["Date", "Title", "Category", "Account", "Amount", "Currency", "Type", "Recurring"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No transactions yet.")

# -------------------------------
# Footer
# -------------------------------
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center; font-size:0.9em; color:#c2185b;'>© 2025 AI-Integrated Financial Management Web Application | Designed with 👑 using Streamlit </p>",
    unsafe_allow_html=True
)

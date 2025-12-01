import streamlit as st
import pandas as pd
from datetime import date
from sqlalchemy import update
from database import init_db, get_transactions_df, Transaction, SessionLocal
import requests

# -------------------------------
# Constants
# -------------------------------
CATEGORIES = ["Bills", "Education", "Entertainment", "Family", "Food", "Grocery", "Health", "Insurance", "Other", "Transport", "Travel"]
ACCOUNTS = ["Savings Bank", "Salary Bank", "Cash", "Credit Card", "Wallet"]
CURRENCIES = ["MYR", "USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "CNY", "SEK", "NZD", "KRW", "SGD", "NOK", "MXN", "BRL", "ZAR", "RUB", "TRY", "AED", "INR", "PHP", "IDR", "THB", "VND", "PKR", "BDT", "LKR", "MMK", "EGP"]

currency_symbol_map = {
    "MYR": "RM", "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
    "INR": "₹", "SGD": "S$", "AUD": "A$", "CAD": "C$", "CHF": "Fr",
    "CNY": "¥", "KRW": "₩", "AED": "د.إ", "THB": "฿", "IDR": "Rp",
    "PHP": "₱", "ZAR": "R", "BRL": "R$", "MXN": "$", "TRY": "₺",
}

# -------------------------------
# FIXED: Removed st.warning to make it cache-safe
# -------------------------------
def get_exchange_rate(base="MYR", target="MYR"):
    if base == target:
        return 1.0
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{base}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data['rates'].get(target, 1.0)
    except Exception:
        pass  # Silent fallback — do NOT use st.warning here
    return 1.0

# -------------------------------
# Authentication Guard
# -------------------------------
if not st.session_state.get("logged_in"):
    st.error("Please log in first.")
    if st.button("Go to Login"):
        st.session_state.clear()
        st.switch_page("app.py")
    st.stop()

# Auto-refresh when coming back from Add Transaction page
if st.session_state.get("new_transaction_added"):
    st.session_state.refresh_now = True
    st.session_state.new_transaction_added = False

# -------------------------------
# Read selected display currency
# -------------------------------
selected_display_currency = st.session_state.get("selected_currency", "MYR")
exchange_rate = get_exchange_rate("MYR", selected_display_currency)
display_symbol = currency_symbol_map.get(selected_display_currency, selected_display_currency + " ")

# Show warning only in main flow (not in cache)
if exchange_rate == 1.0 and selected_display_currency != "MYR":
    st.warning("⚠️ Using fallback exchange rate (API error).")

# -------------------------------
# Page Setup
# -------------------------------
st.set_page_config(
    page_title="Manage Records",
    page_icon="📝",
    layout="wide"
)

# Logout button in sidebar
with st.sidebar:
    st.markdown(f"**Display Currency:** {selected_display_currency} ({display_symbol})")
    if st.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.switch_page("app.py")
        st.stop()

# -------------------------------
# Custom CSS
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
    h1 {
        color: black;
        text-align: center;
        font-weight: 600;
        margin-bottom: 8px;
    }
    .subtitle {
        text-align: center;
        color: #c2185b;
        font-size: 0.95em;
        margin-top: -10px;
        margin-bottom: 24px;
    }
    .filter-box {
        background: white;
        padding: 16px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(145deg, #ec407a, #d81b60) !important;
        color: white !important;
        border: none !important;
        padding: 10px 20px !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(216,27,96,0.3) !important;
        width: 100% !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
    }
    .action-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 4px;
        padding: 6px 10px !important;
        border-radius: 8px !important;
        font-size: 0.85em;
        font-weight: 500;
        border: 1px solid #e2e8f0;
        background-color: white;
        color: #4a5568;
        transition: all 0.2s ease;
        min-width: auto;
        height: 34px;
    }
    .action-btn.edit {
        color: #1976d2;
        border-color: #bbdefb;
    }
    .action-btn.edit:hover {
        background-color: #e3f2fd;
        border-color: #90caf9;
    }
    .action-btn.delete {
        color: #d32f2f;
        border-color: #ffcdd2;
    }
    .action-btn.delete:hover {
        background-color: #ffebee;
        border-color: #f8bbd0;
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
    hr {
        margin: 12px 0;
        border-color: #f0e6f6;
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
        if st.button("←", key="back_to_dashboard", help="Return to Dashboard", type="secondary"):
            st.session_state.pop("is_income", None)
            st.session_state.pop("edit_id", None)
            st.switch_page("pages/dashboard.py")
    with col_title:
        st.markdown("<h1>📝 Manage Financial Records</h1>", unsafe_allow_html=True)
        st.markdown('<p class="subtitle">Review, edit, or delete your transactions anytime.</p>', unsafe_allow_html=True)
    with col_spacer:
        st.write("")

# -------------------------------
# Optimized Data Loading with Caching
# -------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def load_and_convert_data(selected_currency: str, _buster: int = 0):
    df = get_transactions_df()
    if df.empty:
        return df
    rate = get_exchange_rate("MYR", selected_currency)
    df['display_amount'] = df['amount'] * rate
    df['Type_Display'] = df['type'].map({'INCOME': 'Income', 'EXPENSE': 'Expense'})
    return df.copy()

# CRITICAL: Clear ALL caches and force refresh
if st.session_state.get("refresh_now"):
    st.cache_data.clear()
    if "filtered_df" in st.session_state:
        del st.session_state.filtered_df
    st.session_state.refresh_now = False

cache_buster = st.session_state.get("cache_buster", 0)
if st.session_state.get("force_refresh"):
    cache_buster += 1
    st.session_state.cache_buster = cache_buster
    st.session_state.force_refresh = False

df_full = load_and_convert_data(selected_display_currency, cache_buster)

if df_full.empty:
    st.info("No records found. Add your first transaction!")
    st.stop()
    
# -------------------------------
# Helper Functions
# -------------------------------
def parse_amount(amount_str):
    if not amount_str or not str(amount_str).strip():
        raise ValueError("Amount is required.")
    cleaned = ''.join(ch for ch in str(amount_str) if ch.isdigit() or ch in '.-')
    try:
        value = float(cleaned)
        if value <= 0:
            raise ValueError("Amount must be greater than 0.")
        return value
    except ValueError:
        raise ValueError("Invalid amount. Please enter a number (e.g., 100 or 1,234.50).")

# -------------------------------
# FILTER LOGIC (only re-run when filters change)
# -------------------------------
st.markdown("### Search & Filter")
with st.expander("Show Filters", expanded=False):
    filter_key = "filters"
    if filter_key not in st.session_state:
        st.session_state[filter_key] = {}

    col1, col2, col3 = st.columns(3)
    with col1:
        search_query = st.text_input("Search (Title or Category)", placeholder="e.g., Grocery, Salary")
    with col2:
        type_filter = st.multiselect(
            "Type",
            options=["EXPENSE", "INCOME"],
            format_func=lambda x: "Expense" if x == "EXPENSE" else "Income"
        )
    with col3:
        account_filter = st.multiselect("Account", options=sorted(df_full['account'].dropna().unique()))

    col4, col5, col6 = st.columns(3)
    with col4:
        currency_filter = st.multiselect("Original Currency", options=sorted(df_full['currency'].dropna().unique()))
    with col5:
        min_date = st.date_input("From Date", value=df_full['date'].min().date())
    with col6:
        max_date = st.date_input("To Date", value=date.today())

    current_filters = {
        "search": search_query,
        "type": tuple(type_filter),
        "account": tuple(account_filter),
        "currency": tuple(currency_filter),
        "min_date": min_date,
        "max_date": max_date
    }

    if st.session_state[filter_key] != current_filters:
        st.session_state[filter_key] = current_filters
        st.session_state.filtered_df = None

# Apply filters (cached per filter state)
if st.session_state.get("filtered_df") is None:
    df = df_full.copy()
    
    if search_query:
        mask = (
            df['title'].str.contains(search_query, case=False, na=False) |
            df['category'].str.contains(search_query, case=False, na=False)
        )
        df = df[mask]
    if type_filter:
        df = df[df['type'].isin(type_filter)]
    if account_filter:
        df = df[df['account'].isin(account_filter)]
    if currency_filter:
        df = df[df['currency'].isin(currency_filter)]
    df = df[
        (df['date'].dt.date >= min_date) &
        (df['date'].dt.date <= max_date)
    ].sort_values('date', ascending=False).reset_index(drop=True)
    
    st.session_state.filtered_df = df

df_filtered = st.session_state.filtered_df
st.markdown(f"### Showing **{len(df_filtered)}** of **{len(df_full)}** records")

if df_filtered.empty:
    st.warning("No records match your filters.")
    st.stop()

# -------------------------------
# Edit Mode
# -------------------------------
if st.session_state.get('edit_id'):
    edit_row = df_full[df_full['id'] == st.session_state.edit_id].iloc[0]
    st.markdown("### Edit Transaction")
    
    with st.form("edit_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            name = st.text_input("Name", value=edit_row['title'])
            category = st.selectbox(
                "Category",
                options=CATEGORIES,
                index=CATEGORIES.index(edit_row['category']) if edit_row['category'] in CATEGORIES else 8
            )
            account = st.selectbox(
                "Account",
                options=ACCOUNTS,
                index=ACCOUNTS.index(edit_row['account']) if edit_row['account'] in ACCOUNTS else 2
            )
        with col_b:
            amount_input = st.text_input("Amount (in MYR)", value=f"{edit_row['amount']:,.2f}")
            currency = st.selectbox(
                "Original Currency",
                options=CURRENCIES,
                index=CURRENCIES.index(edit_row['currency']) if edit_row['currency'] in CURRENCIES else 0
            )
            trans_type = st.radio("Type", ["Expense", "Income"], index=0 if edit_row['type'] == 'EXPENSE' else 1)
            trans_date = st.date_input("Date", value=edit_row['date'].date())

        col1, col2 = st.columns(2)
        with col1:
            save_clicked = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
        with col2:
            cancel_clicked = st.form_submit_button("Cancel", use_container_width=True)

        if save_clicked:
            try:
                new_amount = parse_amount(amount_input)
                session = SessionLocal()
                try:
                    session.execute(
                        update(Transaction).where(Transaction.id == st.session_state.edit_id).values(
                            title=name,
                            amount=new_amount,
                            category=category,
                            account=account,
                            currency=currency,
                            type='EXPENSE' if trans_type == "Expense" else 'INCOME',
                            date=trans_date
                        )
                    )
                    session.commit()
            
                    st.cache_data.clear()
                    st.session_state.refresh_now = True
                    if "filtered_df" in st.session_state:
                        del st.session_state.filtered_df

                    st.success("✅ Updated successfully!")
                    st.session_state.edit_id = None
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    raise e
                finally:
                    session.close()
            except Exception as e:
                st.error(f"❌ Error: {e}")
        elif cancel_clicked:
            st.session_state.edit_id = None
            st.rerun()

# -------------------------------
# Delete Confirmation
# -------------------------------
elif 'confirm_delete_id' in st.session_state:
    st.warning("⚠️ Are you sure you want to delete this transaction? This action cannot be undone.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Yes, Delete", type="primary", use_container_width=True):
            session = SessionLocal()
            try:
                trans = session.query(Transaction).filter(Transaction.id == st.session_state.confirm_delete_id).first()
                if trans:
                    session.delete(trans)
                    session.commit()
                    st.cache_data.clear()
                    st.session_state.refresh_now = True
                    if "filtered_df" in st.session_state:
                        del st.session_state.filtered_df

                    st.success("✅ Deleted successfully!")
                    
                del st.session_state.confirm_delete_id
                st.rerun()
            except Exception as e:
                session.rollback()
                st.error(f"❌ Error: {e}")
            finally:
                session.close()
    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            del st.session_state.confirm_delete_id
            st.rerun()

# -------------------------------
# Display Records — WITH BEAUTIFUL PAGINATION
# -------------------------------
else:
    # Pagination setup
    PAGE_SIZE = 20
    total_pages = max(1, (len(df_filtered) - 1) // PAGE_SIZE + 1)
    
    if "current_page" not in st.session_state:
        st.session_state.current_page = 1

    # -------------------------------
    # BEAUTIFUL PAGINATION DESIGN
    # -------------------------------
    st.markdown("<br>", unsafe_allow_html=True)

    pagination_cols = st.columns([1, 3, 1])

    with pagination_cols[0]:
        if st.session_state.current_page > 1:
            if st.button("← Previous", key="prev_page", use_container_width=True):
                st.session_state.current_page -= 1
                st.rerun()
        else:
            st.button("← Previous", disabled=True, use_container_width=True)

    with pagination_cols[1]:
        # Centered page indicator
        st.markdown(
            f"""
            <div style="
                display: flex;
                justify-content: center;
                align-items: center;
                background: #f8f9fa;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                color: #4a5568;
                border: 1px solid #e2e8f0;
                font-size: 0.9em;
            ">
                Page <span style="color: #d81b60; margin: 0 4px;">{st.session_state.current_page}</span> of {total_pages}
            </div>
            """,
            unsafe_allow_html=True
        )

    with pagination_cols[2]:
        if st.session_state.current_page < total_pages:
            if st.button("Next →", key="next_page", use_container_width=True):
                st.session_state.current_page += 1
                st.rerun()
        else:
            st.button("Next →", disabled=True, use_container_width=True)

    # Get current page data
    start_idx = (st.session_state.current_page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    page_df = df_filtered.iloc[start_idx:end_idx]

    # Display table header
    header_cols = st.columns([2.2, 1.5, 1.3, 1.2, 1.2, 1.0, 0.8])
    header_cols[0].markdown("**Title**")
    header_cols[1].markdown(f"**Amount ({selected_display_currency})**")
    header_cols[2].markdown("**Category**")
    header_cols[3].markdown("**Account**")
    header_cols[4].markdown("**Type**")
    header_cols[5].markdown("**Date**")
    header_cols[6].markdown("**Actions**")
    st.divider()

    # Display only current page rows
    for _, row in page_df.iterrows():
        cols = st.columns([2.2, 1.5, 1.3, 1.2, 1.2, 1.0, 0.8])
        cols[0].write(row['title'])
        cols[1].write(f"{display_symbol} {row['display_amount']:,.2f}")
        cols[2].write(row['category'])
        cols[3].write(row['account'])
        cols[4].write(row['Type_Display'])
        cols[5].write(row['date'].strftime('%Y-%m-%d'))
        
        with cols[6]:
            col_edit, col_del = st.columns(2)
            with col_edit:
                if st.button("✏️", key=f"edit_{row['id']}", help="Edit", use_container_width=True):
                    st.session_state.edit_id = row['id']
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"del_{row['id']}", help="Delete", use_container_width=True):
                    st.session_state.confirm_delete_id = row['id']
                    st.rerun()

# -------------------------------
# Footer
# -------------------------------
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    f"<p style='text-align:center; font-size:0.9em; color:#c2185b;'>"
    f"© 2025 AI-Integrated Financial Management Web Application | "
    f"Display Currency: {selected_display_currency} | Designed with 👑 using Streamlit </p>",
    unsafe_allow_html=True
)

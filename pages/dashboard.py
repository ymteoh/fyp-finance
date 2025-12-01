# pages/dashboard.py
# FINAL VERSION — Fully migrated to finance.db + Multi-Currency Support

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import requests
import warnings
import base64
from database import init_db, add_transaction, get_last_n, format_display_df
warnings.filterwarnings("ignore")

# -------------------------------
# Login Check
# -------------------------------
if not st.session_state.get("logged_in"):
    st.error("Please log in first.")
    if st.button("Go to Login"):
        st.session_state.clear()
        st.switch_page("app.py")
    st.stop()

# ------------------------------------------------
# PAGE CONFIG & MODERN PINK THEME
# ------------------------------------------------
st.set_page_config(
    page_title="AI Financial Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {
        background-color: white !important;
    }
    .main {
        background-color: white !important;
        padding: 2rem;
    }
    .stMetric {
        background: white;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 6px 16px rgba(216, 27, 96, 0.15);
        border: 1px solid #f0e6f0;
        transition: transform 0.2s ease;
    }
    .stMetric:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 24px rgba(216, 27, 96, 0.25);
    }
    h1, h2, h3, h4, h5 {
        color: #c2185b;
        font-weight: 600;
    }
    h1 { margin-bottom: 5px; }
    .section-divider {
        margin: 2rem 0;
        border: none;
        border-top: 1px solid #f0e6f0;
    }
    .dataframe {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .footer {
        text-align: center;
        color: #c2185b;
        font-size: 0.9em;
        padding: 1.5rem 0;
        margin-top: 2rem;
        border-top: 1px solid #f0e6f0;
    }
    .plotly-graph-div {
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        border: 1px solid #f5f5f5;
    }
    .main button:hover {
        background-color: #ec407a !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# Currency Configuration (SHARED ACROSS PAGES)
# ────────────────────────────────────────────────
currency_options = [
    "MYR", "USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "CNY", "SEK",
    "NZD", "KRW", "SGD", "NOK", "MXN", "BRL", "ZAR", "RUB", "TRY", "AED",
    "INR", "PHP", "IDR", "THB", "VND", "PKR", "BDT", "LKR", "MMK", "EGP"
]

currency_symbol_map = {
    "MYR": "RM", "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
    "INR": "₹", "SGD": "S$", "AUD": "A$", "CAD": "C$", "CHF": "Fr",
    "CNY": "¥", "KRW": "₩", "AED": "د.إ", "THB": "฿", "IDR": "Rp",
    "PHP": "₱", "ZAR": "R", "BRL": "R$", "MXN": "$", "TRY": "₺",
    "SEK": "kr", "NOK": "kr", "NZD": "NZ$"
}

def get_exchange_rate(base="MYR", target="MYR"):
    if base == target:
        return 1.0
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{base}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data['rates'].get(target, 1.0)
    except Exception as e:
        st.warning(f"⚠️ Using MYR (API error: {str(e)[:50]}...)")
    return 1.0

# ────────────────────────────────────────────────
# TITLE & SUBTITLE
# ────────────────────────────────────────────────
# Load circular logo
with open("logo_circle.png", "rb") as f:
    logo_base64 = base64.b64encode(f.read()).decode()

# 🎯 MATCH THE BOTTOM HEADER EXACTLY — LARGE LOGO + TITLE + SUBTITLE TIGHTLY UNDER TITLE
st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 8px;">
        <img 
            src="data:image/png;base64,{logo_base64}" 
            alt="Financial AI Logo"
            style="width: 108px; height: 108px; 
                   border-radius: 50%; 
                   object-fit: contain;
                   vertical-align: middle;"
        >
        <div>
            <h1 style="color: #333; font-weight: 700; font-size: 2.8em; margin: 0;">
                AI-Integrated Financial Management Dashboard
            </h1>
            <p style="color: #c2185b; font-size: 1.3em; margin: -4px 0 0 0; font-weight: 500; line-height: 1.1;">
                Interactive • Insightful • Real-Time
            </p>
        </div>
    </div>
""", unsafe_allow_html=True)

st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# LOAD DATA FROM finance.db
# ────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_data():
    try:
        conn = sqlite3.connect("finance.db")
        query = """
        SELECT 
            date, 
            amount, 
            type, 
            COALESCE(category, 'Uncategorized') AS category,
            COALESCE(account, 'Unknown') AS account,
            COALESCE(title, 'No Title') AS title 
        FROM transactions 
        WHERE date IS NOT NULL AND amount IS NOT NULL
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        df['Date'] = pd.to_datetime(df['date'], errors='coerce')
        df['Amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df['Type'] = df['type'].str.strip().str.upper()
        df['Category'] = df['category'].str.strip().str.title()
        df['Account'] = df['account'].str.strip().str.title()
        df['Title'] = df['title'].str.strip()

        df = df.dropna(subset=['Date', 'Amount', 'Type'])
        df = df[df['Type'].isin(['INCOME', 'EXPENSE'])]
        df['Net'] = np.where(df['Type'] == 'INCOME', df['Amount'], -df['Amount'])
        return df
    except Exception as e:
        st.error(f"⚠️ Database error: {e}")
        return pd.DataFrame()

df = load_data()
if df.empty:
    st.info("No transactions found in the database.")
    st.stop()

# ────────────────────────────────────────────────
# SIDEBAR – FILTERS & SETTINGS
# ────────────────────────────────────────────────
st.sidebar.header("⚙️ Dashboard Controls")

max_categories = st.sidebar.slider(
    "📊 Max Categories in Charts",
    min_value=3,
    max_value=15,
    value=11,
    step=1
)

# ✅ CURRENCY SELECTOR WITH SESSION SYNC
def update_currency():
    st.session_state["selected_currency"] = st.session_state["_currency_select"]

# Initialize if not exists
if "selected_currency" not in st.session_state:
    st.session_state["selected_currency"] = "MYR"

selected_currency = st.sidebar.selectbox(
    "💱 Display Currency",
    options=currency_options,
    index=currency_options.index(st.session_state["selected_currency"]),
    key="_currency_select",
    on_change=update_currency
)

if st.sidebar.button(" Logout", type="secondary"):
    st.session_state.clear()
    st.switch_page("app.py")

# ────────────────────────────────────────────────
# APPLY CURRENCY CONVERSION
# ────────────────────────────────────────────────
exchange_rate = get_exchange_rate("MYR", selected_currency)
currency_symbol = currency_symbol_map.get(selected_currency, selected_currency + " ")

df['Amount'] = df['Amount'] * exchange_rate
df['Net'] = df['Net'] * exchange_rate

# ────────────────────────────────────────────────
# METRICS (KPIs)
# ────────────────────────────────────────────────
total_income = df[df['Type'] == 'INCOME']['Amount'].sum()
total_expense = df[df['Type'] == 'EXPENSE']['Amount'].sum()
net_balance = total_income - total_expense

col1, col2, col3 = st.columns(3)
col1.metric("📈 Total Income", f"{currency_symbol} {total_income:,.0f}")
col2.metric("📉 Total Expense", f"{currency_symbol} {total_expense:,.0f}")
col3.metric(
    "⚖️ Net Balance",
    f"{currency_symbol} {net_balance:,.0f}",
    delta=f"{'+' if net_balance >= 0 else ''}{net_balance:,.0f}",
    delta_color="normal"
)

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 1. INCOME vs EXPENSE – DONUT CHART
# ────────────────────────────────────────────────
st.subheader("💸 Income vs Expense")
if total_income == 0 and total_expense == 0:
    st.info("No income or expense data available.")
else:
    pie_data = pd.DataFrame({
        'Type': ['Income', 'Expense'],
        'Amount': [total_income, total_expense]
    })
    fig_pie = px.pie(
        pie_data,
        values='Amount',
        names='Type',
        color_discrete_sequence=['#ec407a', '#ff77a9'],
        hole=0.5,
        title="Distribution of Cash Flow"
    )
    fig_pie.update_traces(
        textinfo='percent',
        textposition='inside',
        hovertemplate=f'<b>%{{label}}</b><br>Amount: {currency_symbol} %{{value:,.0f}}<br>Percentage: %{{percent}}<extra></extra>',
        marker=dict(line=dict(color='#FFFFFF', width=2))
    )
    fig_pie.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=60, b=60),
        height=400
    )
    st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': True})

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 2. EXPENSE BY CATEGORY (FULL WIDTH BELOW)
# ────────────────────────────────────────────────
st.subheader("📊 Expense by Category")

exp_df = df[df['Type'] == 'EXPENSE'].copy()
if exp_df.empty:
    st.info("No expense data available.")
else:
    col_title, col_radio = st.columns([2, 1])
    with col_radio:
        view_option = st.radio(
            "",
            options=["Monthly", "Yearly"],
            index=0,
            horizontal=True,
            key="view_by"
        )

    if view_option == "Monthly":
        grouped = exp_df.groupby([exp_df['Date'].dt.to_period('M'), 'Category'])['Amount'].sum().unstack(fill_value=0)
        grouped.index = grouped.index.to_timestamp()
        title = "Top Expense Categories (Monthly)"
        xaxis_title = "Month"
    else:  # Yearly
        exp_df['Year'] = exp_df['Date'].dt.year
        grouped = exp_df.groupby(['Year', 'Category'])['Amount'].sum().unstack(fill_value=0)
        grouped.index = grouped.index.astype(int)
        title = "Top Expense Categories (Yearly)"
        xaxis_title = "Year"

    top_cats = grouped.sum().sort_values(ascending=False).head(max_categories).index
    data_plot = grouped[top_cats]

    fig_stack = go.Figure()
    colors = px.colors.qualitative.Pastel[:len(data_plot.columns)]
    for i, col in enumerate(data_plot.columns):
        fig_stack.add_trace(go.Bar(
            x=data_plot.index,
            y=data_plot[col],
            name=col,
            marker_color=colors[i % len(colors)],
            hovertemplate=f'<b>%{{x}}</b><br>%{{data.name}}: {currency_symbol} %{{y:,.0f}}<extra></extra>'
        ))
    fig_stack.update_layout(
        barmode='stack',
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=f"Amount ({currency_symbol})",
        height=420,
        legend_title="Category",
        hovermode="x unified",
        margin=dict(t=40, b=40, l=40, r=20),
        font=dict(size=12)
    )
    st.plotly_chart(fig_stack, use_container_width=True, config={'scrollZoom': False})

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 3. INCOME vs EXPENSE BY PAYMENT METHOD (ACCOUNT)
# ────────────────────────────────────────────────
st.subheader("💳 Income vs Expense by Payment Method")

account_flow = df.groupby(['Account', 'Type'])['Amount'].sum().unstack(fill_value=0)
account_flow['Income'] = account_flow.get('INCOME', 0)
account_flow['Expense'] = account_flow.get('EXPENSE', 0)
account_flow['Total'] = account_flow['Income'] + account_flow['Expense']
account_flow = account_flow.sort_values('Total', ascending=True).tail(max_categories)

if not account_flow.empty:
    fig_hbar = go.Figure()
    fig_hbar.add_trace(go.Bar(
        y=account_flow.index,
        x=account_flow['Income'],
        name='Income',
        orientation='h',
        marker_color='#ec407a',
        hovertemplate=f'<b>%{{y}}</b><br>Income: {currency_symbol} %{{x:,.0f}}<extra></extra>'
    ))
    fig_hbar.add_trace(go.Bar(
        y=account_flow.index,
        x=-account_flow['Expense'],
        name='Expense',
        orientation='h',
        marker_color='#b0bec5',
        hovertemplate=f'<b>%{{y}}</b><br>Expense: {currency_symbol} %{{x:,.0f}}<extra></extra>'
    ))
    fig_hbar.update_layout(
        barmode='relative',
        title="Cash Flow by Payment Method",
        xaxis_title=f"Amount ({currency_symbol})",
        height=300 + len(account_flow) * 25,
        hovermode="y unified",
        margin=dict(l=150, r=50, t=50, b=50)
    )
    st.plotly_chart(fig_hbar, use_container_width=True)
else:
    st.info("No account data available.")

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# 4. RECENT TRANSACTIONS
# ────────────────────────────────────────────────
st.subheader("📋 Recent Transactions")

df_raw = get_last_n(15)
if not df_raw.empty:
    # Make a copy to avoid modifying original data
    df_for_display = df_raw.copy()
    
    # Convert amount from MYR (stored) to selected display currency
    df_for_display['amount'] = df_for_display['amount'] * exchange_rate
    
    # Update currency column to show the currently selected display currency
    df_for_display['currency'] = selected_currency
    
    # Ensure 'date' is datetime for the formatter (in case it's string from DB)
    df_for_display['date'] = pd.to_datetime(df_for_display['date'], errors='coerce')
    
    # Apply your shared formatting function
    df_disp = format_display_df(df_for_display)
    
    # Display in the same order as Add Transaction page
    st.dataframe(
        df_disp[["Date", "Title", "Category", "Account", "Amount", "Currency", "Type", "Recurring"]],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No recent transactions.")
# ────────────────────────────────────────────────
# FOOTER
# ────────────────────────────────────────────────
st.markdown(f"""
<div class="footer">
    © 2025 AI-Integrated Financial Management Web Application | 
    Currency: {selected_currency} ({currency_symbol}) | Designed with 👑 using Streamlit 
</div>   
""", unsafe_allow_html=True)
import streamlit as st
import google.generativeai as genai
import os
import pandas as pd
import sqlite3
import requests
from datetime import datetime
from dotenv import load_dotenv

# -------------------------------
# Load environment variables (from .env)
# -------------------------------
load_dotenv()

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
    page_title="Financial Assistant",
    page_icon="💬",
    layout="wide"
)

# -------------------------------
# Custom CSS (Pink theme + clean UI)
# -------------------------------
st.markdown("""
    <style>
    .main { background-color: white; font-family: 'Segoe UI', sans-serif; }
    [data-testid="stAppViewContainer"] { background-color: white !important; }
    .back-as-text {
        background: none !important; border: none !important; padding: 0 !important;
        color: #d81b60 !important; font-weight: 600 !important; text-align: left !important;
        cursor: pointer !important; font-size: 16px !important; text-decoration: none !important;
        width: auto !important; box-shadow: none !important;
    }
    .back-as-text:hover { text-decoration: underline !important; color: #c2185b !important; }
    .stSidebar .stButton > button {
        background: white !important; color: #333 !important; border: 1px solid #ddd !important;
        box-shadow: none !important; border-radius: 8px !important; padding: 8px 16px !important;
        font-weight: normal !important; width: auto !important; transform: none !important;
    }
    .stSidebar .stButton > button:hover {
        background: #f8f8f8 !important; border-color: #ccc !important;
    }
    .user-msg {
        max-width: 85%; margin-left: auto; margin-right: 0; padding: 16px 20px;
        border-radius: 12px 12px 0 12px; background: linear-gradient(145deg, #ec407a, #d81b60);
        color: white; font-size: 15px; line-height: 1.6; box-shadow: 0 4px 12px rgba(216, 27, 96, 0.3);
    }
    .bot-msg-container {
        display: flex; gap: 12px; align-items: flex-start; max-width: 900px; margin: 0 auto; width: 100%;
        justify-content: flex-start;
    }
    .bot-avatar {
    width: 48px; height: 48px; border-radius: 16px; overflow: hidden;
    flex-shrink: 0; box-shadow: 0 6px 20px rgba(216, 27, 96, 0.4);
    border: 3px solid #d81b60;
    }
    .bot-avatar img {
        width: 100%; height: 100%; object-fit: cover;
    }
    .bot-msg {
        flex: 1; padding: 16px 20px; border-radius: 12px; background: white; color: #333;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); border: 1px solid rgba(236, 64, 122, 0.2);
        font-size: 15px; line-height: 1.6;
    }
    .typing-indicator {
        display: flex; align-items: center; gap: 8px; padding: 16px 20px; border-radius: 12px;
        background: white; border: 1px solid rgba(236, 64, 122, 0.2); box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        font-size: 15px; color: #666;
    }
    .typing-dot {
        width: 6px; height: 6px; border-radius: 50%; background-color: #ec407a; opacity: 0.8;
        animation: blink 1.4s infinite both;
    }
    @keyframes blink {
        0%, 80%, 100% { transform: translateY(0); opacity: 0.8; }
        40% { transform: translateY(-4px); opacity: 1; }
    }
    .typing-dot:nth-child(2) { animation-delay: 0.2s; }
    .typing-dot:nth-child(3) { animation-delay: 0.4s; }
    .input-wrapper { position: relative; width: 100%; max-width: 900px; margin: 20px auto; }
    .chat-input { width: 100%; padding: 16px 50px 16px 20px; border: 1px solid #ec407a44;
        border-radius: 12px; font-size: 15px; outline: none; transition: all 0.2s ease;
        background: rgba(236, 64, 122, 0.05); }
    .chat-input:focus { border-color: #d81b60; box-shadow: 0 0 0 2px rgba(216, 27, 96, 0.2); }
    .send-btn {
        position: absolute; right: 32px; top: 50%; transform: translateY(-50%);
        background: #d81b60; color: white; border: none; width: 36px; height: 36px;
        border-radius: 50%; font-size: 18px; font-weight: bold; cursor: pointer;
        display: flex; align-items: center; justify-content: center;
    }
    .quick-suggestion {
        display: inline-block; padding: 8px 16px; margin: 4px; border-radius: 24px;
        background: rgba(236, 64, 122, 0.1); border: 1px solid rgba(236, 64, 122, 0.2);
        font-size: 13px; color: #d81b60; cursor: pointer; transition: all 0.2s ease;
    }
    .quick-suggestion:hover {
        background: rgba(236, 64, 122, 0.2); transform: translateY(-1px);
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------
# Header: Back + Title
# -------------------------------
header_container = st.container()
with header_container:
    col_back, col_title, col_spacer = st.columns([0.5, 4, 0.5])
    with col_back:
        if st.button("←", key="back_to_dashboard", help="Return to Dashboard"):
            if "is_income" in st.session_state:
                del st.session_state["is_income"]
            st.switch_page("pages/dashboard.py")
    with col_title:
        st.markdown("<h1 style='text-align: center'>💬 Financial Assistant</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #c2185b; font-size: 0.9em;'>Your AI-powered financial analyst — ask anything about income, expenses, or trends.</p>", unsafe_allow_html=True)
    with col_spacer:
        st.write("")

# -------------------------------
# Sidebar
# -------------------------------
with st.sidebar:
    st.markdown("<h3 style='color:#d81b60;'>💬 Financial Assistant</h3>", unsafe_allow_html=True)
    st.markdown("---")
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.session_state.is_typing = False
        st.rerun()

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.switch_page("app.py")

# -------------------------------
# Currency Support (Sync with Dashboard)
# -------------------------------
selected_currency = st.session_state.get("selected_currency", "MYR")

def get_exchange_rate(base="MYR", target="MYR"):
    if base == target:
        return 1.0
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{base}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data['rates'].get(target, 1.0)
    except:
        return 1.0

exchange_rate = get_exchange_rate("MYR", selected_currency)
currency_symbol = {
    "MYR": "RM", "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
    "INR": "₹", "SGD": "S$", "AUD": "A$", "CAD": "C$", "CHF": "Fr",
    "CNY": "¥", "KRW": "₩", "AED": "د.إ", "THB": "฿", "IDR": "Rp",
    "PHP": "₱", "ZAR": "R", "BRL": "R$", "MXN": "$", "TRY": "₺",
    "SEK": "kr", "NOK": "kr", "NZD": "NZ$"
}.get(selected_currency, selected_currency + " ")

# Welcome message (SAFE)
welcome_msg = f"Hi! I'm <strong>Financial Assistant</strong>. I can analyze your finances in <strong>{selected_currency} ({currency_symbol})</strong>. Ask me about spending, income, or trends!"

if "messages" not in st.session_state or not st.session_state.messages:
    st.session_state.messages = [{"role": "model", "content": welcome_msg}]
elif st.session_state.messages and "Financial Assistant" in st.session_state.messages[0]["content"]:
    # Only update if currency changed
    if selected_currency not in st.session_state.messages[0]["content"]:
        st.session_state.messages[0]["content"] = welcome_msg

# -------------------------------
# Load Data from finance.db
# -------------------------------
@st.cache_data(ttl=300)
def load_data_from_db():
    try:
        conn = sqlite3.connect("finance.db")
        df = pd.read_sql_query("""
            SELECT date, title, category, account, amount, currency, type, is_recurring
            FROM transactions 
            WHERE date IS NOT NULL AND amount IS NOT NULL
        """, conn)
        conn.close()
        
        df['Date'] = pd.to_datetime(df['date'], errors='coerce')
        df['Amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df['Type'] = df['type'].str.strip().str.upper()
        df['Category'] = df['category'].str.strip().str.title()
        df['Account'] = df['account'].str.strip().str.title()
        df['Title'] = df['title'].str.strip()
        df['Is_Recurring'] = pd.to_numeric(df['is_recurring'], errors='coerce').fillna(0)
        
        return df.dropna(subset=['Date', 'Amount', 'Type'])
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

df = load_data_from_db()

# ------------------
# Helper Functions 
# ------------------
def get_last_5_transactions(df, exchange_rate, currency_symbol):
    if df.empty:
        return "No transactions found."
    recent = df.sort_values('Date', ascending=False).head(5)
    rows = []
    for _, r in recent.iterrows():
        amt = r['Amount'] * exchange_rate
        date_str = r['Date'].strftime('%Y-%m-%d')
        rows.append(f"{date_str}: {r['Title']} → {currency_symbol}{amt:,.2f} ({r['Category']})")
    return "📋 <strong>Last 5 Transactions</strong>:<br><br>" + "<br>".join(rows)

def get_total_income(df, exchange_rate, currency_symbol, monthly=False):
    if df.empty:
        return "No income data."
    
    income_df = df[df['Type'] == 'INCOME'].copy()
    if income_df.empty:
        return "✅ No income recorded."

    if monthly:
        this_month = pd.Timestamp.today().to_period('M')
        income_df = income_df[income_df['Date'].dt.to_period('M') == this_month]
        if income_df.empty:
            return "✅ No income recorded this month."

    total = income_df['Amount'].sum() * exchange_rate
    period = "this month" if monthly else "total"
    return f"📈 <strong>Total Income ({period})</strong>: {currency_symbol}{total:,.2f}"

def get_net_balance(df, exchange_rate, currency_symbol, monthly=False):
    if df.empty:
        return "No transaction data."

    this_month = pd.Timestamp.today().to_period('M') if monthly else None
    if monthly:
        df = df[df['Date'].dt.to_period('M') == this_month]
        if df.empty:
            return "✅ No transactions recorded this month."

    income = df[df['Type'] == 'INCOME']['Amount'].sum() * exchange_rate
    expense = df[df['Type'] == 'EXPENSE']['Amount'].sum() * exchange_rate
    balance = income - expense
    status = "Profit" if balance >= 0 else "Loss"
    period = "this month" if monthly else "total"
    return f"💰 <strong>Net Balance ({period})</strong>: {currency_symbol}{balance:,.2f} ({status})"

def get_top_expense_category(df, exchange_rate, currency_symbol):
    expense_df = df[df['Type'] == 'EXPENSE']
    if expense_df.empty:
        return "No expense data."
    top_cat = expense_df.groupby('Category')['Amount'].sum().sort_values(ascending=False).index[0]
    top_amt = expense_df[expense_df['Category'] == top_cat]['Amount'].sum() * exchange_rate
    return f"🔥 <strong>Top Expense Category</strong>: <strong>{top_cat}</strong> → {currency_symbol}{top_amt:,.2f}"

def get_spending_alert(df, exchange_rate, currency_symbol):
    if df.empty:
        return "No transactions yet."
    
    df['Month'] = df['Date'].dt.to_period('M')
    this_month = pd.Timestamp.today().to_period('M')
    
    current = df[(df['Month'] == this_month) & (df['Type'] == 'EXPENSE')]
    if current.empty:
        # Clear alert context
        if "alert_category" in st.session_state:
            del st.session_state["alert_category"]
        if "alert_amount" in st.session_state:
            del st.session_state["alert_amount"]
        return "✅ No spending this month yet. Great start!"
    
    past = df[(df['Month'] < this_month) & (df['Type'] == 'EXPENSE')]
    if past.empty:
        if "alert_category" in st.session_state:
            del st.session_state["alert_category"]
        if "alert_amount" in st.session_state:
            del st.session_state["alert_amount"]
        return "✅ Not enough past data for alerts. Keep tracking!"
    
    avg_by_cat = past.groupby('Category')['Amount'].sum() / len(past['Month'].unique())
    alerts = []
    for cat, avg in avg_by_cat.items():
        spent = current[current['Category'] == cat]['Amount'].sum() * exchange_rate
        avg_amt = avg * exchange_rate
        if spent > 0.8 * avg_amt:
            alerts.append(f"⚠️ <strong>{cat}</strong>: {currency_symbol}{spent:,.0f} (80%+ of avg {currency_symbol}{avg_amt:,.0f})")
            # Save the FIRST overspending category and its THIS MONTH amount
            st.session_state["alert_category"] = cat
            st.session_state["alert_amount"] = spent
            break  # Only handle the first overspending category for simplicity
    
    if not alerts:
        if "alert_category" in st.session_state:
            del st.session_state["alert_category"]
        if "alert_amount" in st.session_state:
            del st.session_state["alert_amount"]
        return "✅ All categories under control this month. Excellent!"
    
    return ("🚨 <strong>Spending Alerts</strong>:<br>" + 
            "<br>".join(alerts) + 
            "<br><br>💬 Type <strong>'action plan'</strong> to get AI steps to fix this!")

def get_budget_tip(df, exchange_rate, currency_symbol):
    # ✅ Filter to THIS MONTH only
    df['Month'] = df['Date'].dt.to_period('M')
    this_month = pd.Timestamp.today().to_period('M')
    current_month_expense = df[(df['Month'] == this_month) & (df['Type'] == 'EXPENSE')]
    
    if current_month_expense.empty:
        return "✅ No expenses this month yet. Great start!"
    
    # ✅ Get top 3 categories THIS MONTH
    top3 = current_month_expense.groupby('Category')['Amount'].sum().nlargest(3)
    tips = []
    for cat, amt in top3.items():
        amt_fmt = amt * exchange_rate
        save_20 = amt_fmt * 0.2
        tips.append(f"💡 <strong>{cat}</strong> → {currency_symbol}{amt_fmt:,.0f}<br>   Cut 20% → Save {currency_symbol}{save_20:,.0f}/month")
    
    return ("💡 <strong>Personal Budget Tips (This Month)</strong>:<br><br>" +
            "<br><br>".join(tips) +
            "<br><br>💬 Type <strong>'detailed tips for [Category]'</strong> (e.g., 'detailed tips for Family') to get specific ways to save!")
    
def get_forecast_summary(df, exchange_rate, currency_symbol):
    if df.empty:
        return "📊 <strong>FORECAST INSIGHT</strong>:<br>No transaction data available for forecasting."
    
    # Income forecast (3-month avg or total)
    income_df = df[df['Type'] == 'INCOME'].copy()
    if not income_df.empty:
        income_df.set_index('Date', inplace=True)
        if len(income_df) >= 30:  # At least 30 days of data
            income_3m = income_df['Amount'].resample('M').sum().tail(3).mean()
        else:
            income_3m = income_df['Amount'].sum() / max(len(income_df['Date'].dt.to_period('M').unique()), 1)
        income_next = income_3m * exchange_rate
    else:
        income_next = 0

    # Expense forecast (3-month avg or total)
    expense_df = df[df['Type'] == 'EXPENSE'].copy()
    if not expense_df.empty:
        expense_df.set_index('Date', inplace=True)
        if len(expense_df) >= 30:
            expense_3m = expense_df['Amount'].resample('M').sum().tail(3).mean()
        else:
            expense_3m = expense_df['Amount'].sum() / max(len(expense_df['Date'].dt.to_period('M').unique()), 1)
        expense_next = expense_3m * exchange_rate
    else:
        expense_next = 0

    net_next = income_next - expense_next
    status = "surplus" if net_next >= 0 else "deficit"
    
    return (f"📈 <strong>Forecast Summary (Next Month)</strong>:<br><br>"
            f"• <strong>Income</strong>: {currency_symbol}{income_next:,.0f}<br>"
            f"• <strong>Expenses</strong>: {currency_symbol}{expense_next:,.0f}<br>"
            f"• <strong>Net</strong>: {currency_symbol}{net_next:,.0f} ({status})<br><br>"
            f"ℹ️ <em>Based on 3-month average. For detailed AI-powered forecasts, visit the <strong>Trend & Prediction</strong> page.</em>")

def get_recurring_audit(df, exchange_rate, currency_symbol):
    """Analyze recurring expenses and flag potential waste."""
    recurring = df[(df['Is_Recurring'] == 1) & (df['Type'] == 'EXPENSE')]
    if recurring.empty:
        return "✅ No recurring expenses found."

    # Group by category and calculate avg monthly cost
    recurring = recurring.copy()
    recurring['Month'] = recurring['Date'].dt.to_period('M')
    monthly_avg = recurring.groupby('Category').agg(
        total_amount=('Amount', 'sum'),
        months_active=('Month', 'nunique')
    )
    monthly_avg['avg_monthly'] = (monthly_avg['total_amount'] / monthly_avg['months_active']) * exchange_rate

    # Find latest transaction per category for inactivity check
    latest_tx = recurring.loc[recurring.groupby('Category')['Date'].idxmax()]
    today = pd.Timestamp.today()
    lines = []
    for cat, row in monthly_avg.iterrows():
        avg_amt = row['avg_monthly']
        latest_date = latest_tx[latest_tx['Category'] == cat]['Date'].iloc[0]
        days_since = (today - latest_date).days
        
        if days_since > 60:  # Flag if no use in 60+ days
            lines.append(
                f"⚠️ <strong>{cat}</strong>: {currency_symbol}{avg_amt:,.2f}/month "
                f"<em>(last used {days_since} days ago)</em>"
            )
        else:
            lines.append(f"• <strong>{cat}</strong>: {currency_symbol}{avg_amt:,.2f}/month")

    return ("🔁 <strong>Recurring Expense Audit</strong>:<br>" + 
            "<br>".join(lines) + 
            "<br><br>💡 Tip: Cancel unused subscriptions to boost your net balance.")

def get_mom_trend(df, exchange_rate, currency_symbol):
    """Calculate MoM % change in total expenses."""
    expenses = df[df['Type'] == 'EXPENSE'].copy()
    if expenses.empty:
        return "✅ No expense data to analyze."

    expenses.set_index('Date', inplace=True)
    monthly = expenses['Amount'].resample('M').sum() * exchange_rate
    if len(monthly) < 2:
        return "📈 Only one month of data—trend analysis requires ≥2 months."

    current = monthly.iloc[-1]
    prior = monthly.iloc[-2]
    pct_change = ((current - prior) / prior) * 100 if prior != 0 else 0

    # Find top growing category
    current_month = expenses[expenses.index.to_period('M') == monthly.index[-1].to_period('M')]
    prior_month = expenses[expenses.index.to_period('M') == monthly.index[-2].to_period('M')]
    
    cat_current = current_month.groupby('Category')['Amount'].sum()
    cat_prior = prior_month.groupby('Category')['Amount'].sum()
    cat_change = (cat_current - cat_prior).fillna(0) * exchange_rate
    top_cat = cat_change.abs().idxmax() if not cat_change.empty else "Unknown"
    top_delta = cat_change.get(top_cat, 0)

    trend_emoji = "📈" if pct_change > 0 else "📉"
    status = "increasing" if pct_change > 0 else "decreasing"
    
    base_msg = (
        f"{trend_emoji} <strong>MoM Expense Trend</strong>:<br><br>"
        f"• Total spending: <strong>{status}</strong> by <strong>{abs(pct_change):.1f}%</strong><br>"
        f"• Current month: {currency_symbol}{current:,.0f} | Prior: {currency_symbol}{prior:,.0f}<br>"
        f"• Biggest mover: <strong>{top_cat}</strong> ({'+' if top_delta >= 0 else ''}{currency_symbol}{top_delta:,.0f})<br><br>"
        "🔍 <em>Consistent increases may signal need for budget adjustment.</em>"
    )
    
    # Only show CTA if trend is increasing (actionable)
    if pct_change > 0:
        base_msg += "<br><br>💬 Type <strong>'stabilize my trend'</strong> to get AI-powered steps to control rising spending!"
    
    return base_msg

def get_savings_health(df, exchange_rate, currency_symbol):
    """Calculate savings rate and provide benchmark context."""
    if df.empty:
        return "📊 No transaction data available."

    df['Month'] = df['Date'].dt.to_period('M')
    monthly_summary = df.groupby(['Month', 'Type'])['Amount'].sum().unstack(fill_value=0)
    
    if 'INCOME' not in monthly_summary.columns:
        monthly_summary['INCOME'] = 0
    if 'EXPENSE' not in monthly_summary.columns:
        monthly_summary['EXPENSE'] = 0

    monthly_summary['Net'] = monthly_summary['INCOME'] - monthly_summary['EXPENSE']
    monthly_summary['Savings_Rate'] = monthly_summary['Net'] / monthly_summary['INCOME'].replace(0, 1)
    
    # Use most recent month
    latest = monthly_summary.iloc[-1]
    savings_rate = latest['Savings_Rate'] * 100
    net = latest['Net'] * exchange_rate
    income = latest['INCOME'] * exchange_rate

    # Benchmark logic (adjust thresholds as needed)
    if savings_rate >= 20:
        status = "✅ <strong>Excellent</strong> – On track for financial independence."
    elif savings_rate >= 10:
        status = "🔶 <strong>Good</strong> – Healthy buffer; consider boosting to 20%."
    elif savings_rate > 0:
        status = "⚠️ <strong>Fair</strong> – Low cushion; aim for ≥10% savings."
    else:
        status = "❗ <strong>Critical</strong> – Spending exceeds income. Immediate review needed."

    return (
        f"🛡️ <strong>Savings Health Check</strong>:<br><br>"
        f"• Income: {currency_symbol}{income:,.0f}<br>"
        f"• Net Savings: {currency_symbol}{net:,.0f}<br>"
        f"• <strong>Savings Rate: {savings_rate:.1f}%</strong><br><br>"
        f"{status}<br><br>"
        "💡 <em>Target: ≥20% for long-term security (per global best practices).</em>"
    )

def get_cash_flow_stability(df, exchange_rate, currency_symbol):
    """Analyze volatility in monthly income and expenses."""
    if df.empty:
        return "📊 No transaction data available for cash flow analysis."

    # Prepare monthly aggregates
    df = df.copy()
    df['Month'] = df['Date'].dt.to_period('M')
    monthly = df.groupby(['Month', 'Type'])['Amount'].sum().unstack(fill_value=0)
    
    # Ensure both INCOME and EXPENSE columns exist
    if 'INCOME' not in monthly.columns:
        monthly['INCOME'] = 0
    if 'EXPENSE' not in monthly.columns:
        monthly['EXPENSE'] = 0

    # Require at least 2 months of data
    if len(monthly) < 2:
        return "📈 Cash flow stability analysis requires ≥2 months of data."

    # Convert to user currency
    income_series = monthly['INCOME'] * exchange_rate
    expense_series = monthly['EXPENSE'] * exchange_rate

    # Compute coefficient of variation (CV = std / mean)
    income_mean = income_series.mean()
    income_std = income_series.std()
    income_cv = (income_std / income_mean * 100) if income_mean > 0 else float('inf')

    expense_mean = expense_series.mean()
    expense_std = expense_series.std()
    expense_cv = (expense_std / expense_mean * 100) if expense_mean > 0 else float('inf')

    # Interpret stability
    def interpret_cv(cv):
        if cv == float('inf'):
            return "N/A"
        elif cv <= 10:
            return "✅ Very Stable"
        elif cv <= 25:
            return "🔶 Moderately Stable"
        elif cv <= 50:
            return "⚠️ Volatile"
        else:
            return "❗ Highly Volatile"

    income_stability = interpret_cv(income_cv)
    expense_stability = interpret_cv(expense_cv)

    # Net cash flow insight
    net_series = income_series - expense_series
    net_mean = net_series.mean()
    net_buffer_months = (net_mean / expense_mean) if expense_mean > 0 and net_mean > 0 else 0

    # Build response
    response = f"⚖️ <strong>Cash Flow Stability Analysis</strong>:<br><br>"

    if income_cv != float('inf'):
        response += (f"• <strong>Income</strong>: {income_stability} "
                     f"(Avg: {currency_symbol}{income_mean:,.0f}/mo, "
                     f"Volatility: {income_cv:.1f}%)<br>")
    else:
        response += "• <strong>Income</strong>: No income recorded.<br>"

    if expense_cv != float('inf'):
        response += (f"• <strong>Expenses</strong>: {expense_stability} "
                     f"(Avg: {currency_symbol}{expense_mean:,.0f}/mo, "
                     f"Volatility: {expense_cv:.1f}%)<br>")
    else:
        response += "• <strong>Expenses</strong>: No expenses recorded.<br>"

    # Add actionable recommendation
    if net_mean > 0:
        response += f"<br>💡 <strong>Recommendation</strong>:<br>"
        if income_cv > 30 or expense_cv > 30:
            buffer_months = min(6, max(3, int(net_buffer_months * 12)))
            response += (f"With volatile cash flow, maintain a buffer of "
                         f"<strong>≥{buffer_months} months</strong> of expenses "
                         f"({currency_symbol}{expense_mean * buffer_months:,.0f}).")
        else:
            response += ("Your cash flow is relatively stable. A "
                         "<strong>2–3 month expense buffer</strong> is sufficient.")
    else:
        response += "<br>❗ <strong>Warning</strong>: Net cash flow is negative. Prioritize income growth or expense reduction."

    # Add CTA only if volatile or highly volatile
    if income_cv > 30 or expense_cv > 30:
        response += "<br><br>💬 Type <strong>'smooth my cash flow'</strong> to get AI strategies for more predictable finances!"

    return response
# ---------------------------------------
# AI-Powered Action Plan
# ---------------------------------------
def get_alert_action_plan(user_query, df, exchange_rate, currency_symbol):
    """AI plan for spending alerts (uses alert context only)"""
    if df.empty:
        return "No data to analyze."
    
    df['Month'] = df['Date'].dt.to_period('M')
    this_month = pd.Timestamp.today().to_period('M')
    current_month_expense = df[(df['Month'] == this_month) & (df['Type'] == 'EXPENSE')]
    
    if current_month_expense.empty:
        return "✅ No expenses this month. Great job!"
    
    # Use ONLY alert context
    if "alert_category" in st.session_state and "alert_amount" in st.session_state:
        target_cat = st.session_state["alert_category"]
        cat_amt = st.session_state["alert_amount"]
    else:
        # Fallback to this month's top category
        top_cat_series = current_month_expense.groupby('Category')['Amount'].sum().nlargest(1)
        target_cat = top_cat_series.index[0]
        cat_amt = top_cat_series.iloc[0] * exchange_rate
    
    total_expense = current_month_expense['Amount'].sum() * exchange_rate
    
    context = f"""
You are a professional financial coach. 
User's current month spending in category '{target_cat}': {currency_symbol}{cat_amt:,.0f}
Total monthly expense: {currency_symbol}{total_expense:,.0f}
Currency: {selected_currency}
User asked: "{user_query}"

- Give 4-6 PRACTICAL, actionable steps in numbered list.
- Use friendly, encouraging tone.
- Focus on reducing spending in '{target_cat}' this month.
- Keep under 180 words.
"""
    try:
        response = model.generate_content(context)
        return "<strong>YOUR PERSONAL ACTION PLAN</strong><br><br>" + response.text
    except Exception as e:
        return f"AI is busy right now. Error: {str(e)[:50]}..."
    
def get_budget_detailed_tips(user_query, df, exchange_rate, currency_symbol):
    """AI tips for budget categories (requires category in query)"""
    if df.empty:
        return "No data to analyze."
    
    df['Month'] = df['Date'].dt.to_period('M')
    this_month = pd.Timestamp.today().to_period('M')
    current_month_expense = df[(df['Month'] == this_month) & (df['Type'] == 'EXPENSE')]
    
    if current_month_expense.empty:
        return "✅ No expenses this month. Great job!"
    
    # Extract category from "detailed tips for [Category]"
    user_query_clean = user_query.lower().replace("detailed tips for", "").strip()
    detected_cat = None
    
    for cat in current_month_expense['Category'].unique():
        if cat.lower() in user_query_clean or user_query_clean in cat.lower():
            detected_cat = cat
            break
    
    if not detected_cat:
        return "❓ Please specify a category (e.g., 'detailed tips for Family')."
    
    cat_amt = current_month_expense[current_month_expense['Category'] == detected_cat]['Amount'].sum() * exchange_rate
    total_expense = current_month_expense['Amount'].sum() * exchange_rate
    savings_target = cat_amt * 0.2
    
    context = f"""
You are a professional financial coach. 
User spent {currency_symbol}{cat_amt:,.0f} on '{detected_cat}' this month.
They want SPECIFIC ways to save at least 20% ({currency_symbol}{savings_target:,.0f}).

Give 5 CONCRETE, actionable tips to reduce '{detected_cat}' spending:
- Include real examples (e.g., "Switch to generic brands")
- Focus on low-effort, high-impact changes
- Number the tips (1-5)
- Keep under 180 words.
"""
    try:
        response = model.generate_content(context)
        return f"<strong>💡 DETAILED TIPS FOR '{detected_cat}'</strong><br><br>" + response.text
    except Exception as e:
        return f"AI is busy right now. Error: {str(e)[:50]}..."

def get_mom_action_plan(user_query, df, exchange_rate, currency_symbol):
    """Generate AI action plan for rising MoM expenses."""
    if df.empty:
        return "No data to analyze."

    expenses = df[df['Type'] == 'EXPENSE'].copy()
    if expenses.empty or len(expenses['Date'].dt.to_period('M').unique()) < 2:
        return "Not enough data for trend-based advice."

    # Identify top growing category
    expenses.set_index('Date', inplace=True)
    monthly = expenses['Amount'].resample('M').sum()
    current_month = expenses[expenses.index.to_period('M') == monthly.index[-1].to_period('M')]
    prior_month = expenses[expenses.index.to_period('M') == monthly.index[-2].to_period('M')]
    
    cat_current = current_month.groupby('Category')['Amount'].sum()
    cat_prior = prior_month.groupby('Category')['Amount'].sum()
    cat_change = (cat_current - cat_prior).fillna(0)
    if cat_change.empty:
        top_cat = "General"
        delta = 0
    else:
        top_cat = cat_change.abs().idxmax()
        delta = cat_change.loc[top_cat] * exchange_rate

    context = f"""
You are a professional financial coach.
User's expenses are rising MoM, driven by '{top_cat}' (+{currency_symbol}{delta:,.0f}).
Currency: {selected_currency}
User wants to control increasing spending.

- Give 4 PRACTICAL, category-specific steps to curb growth in '{top_cat}'.
- Keep under 160 words.
- Numbered list.
- Encouraging but direct tone.
"""
    try:
        response = model.generate_content(context)
        return f"<strong>📉 ACTION PLAN: Control Rising Spending</strong><br><br>" + response.text
    except Exception as e:
        return f"AI is busy. Error: {str(e)[:50]}..."


def get_cash_flow_action_plan(user_query, df, exchange_rate, currency_symbol):
    """Generate AI action plan for volatile cash flow."""
    if df.empty:
        return "No data to analyze."

    df = df.copy()
    df['Month'] = df['Date'].dt.to_period('M')
    monthly = df.groupby(['Month', 'Type'])['Amount'].sum().unstack(fill_value=0)
    if 'INCOME' not in monthly: monthly['INCOME'] = 0
    if 'EXPENSE' not in monthly: monthly['EXPENSE'] = 0
    if len(monthly) < 2:
        return "Not enough data for cash flow advice."

    income_series = monthly['INCOME'] * exchange_rate
    expense_series = monthly['EXPENSE'] * exchange_rate
    income_cv = (income_series.std() / income_series.mean() * 100) if income_series.mean() > 0 else 0
    expense_cv = (expense_series.std() / expense_series.mean() * 100) if expense_series.mean() > 0 else 0

    high_volatility = income_cv > 30 or expense_cv > 30
    avg_expense = expense_series.mean()

    context = f"""
You are a professional financial coach.
User has {'highly volatile' if high_volatility else 'moderate'} cash flow.
Income volatility: {income_cv:.1f}%, Expense volatility: {expense_cv:.1f}%.
Average monthly expense: {currency_symbol}{avg_expense:,.0f}.
Currency: {selected_currency}
User seeks stability.

- Recommend a tailored emergency buffer (in months and {currency_symbol}).
- Suggest 3 steps to smooth income or expenses.
- Keep under 170 words.
- Numbered list.
"""
    try:
        response = model.generate_content(context)
        return f"<strong>🛡️ ACTION PLAN: Stabilize Cash Flow</strong><br><br>" + response.text
    except Exception as e:
        return f"AI is busy. Error: {str(e)[:50]}..."
    
# -------------------------------
# Initialize Chat 
# -------------------------------
current_welcome = f"Hi! I'm <strong>Financial Assistant</strong>. I can analyze your finances in <strong>{selected_currency} ({currency_symbol})</strong>. Ask me about spending, income, or trends!"

# Check if we need to update the welcome message
should_update_welcome = False
if "messages" in st.session_state:
    if len(st.session_state.messages) > 0:
        first_msg = st.session_state.messages[0]
        if "Financial Assistant" in first_msg.get("content", "") and selected_currency not in first_msg.get("content", ""):
            should_update_welcome = True

if "messages" not in st.session_state or should_update_welcome:
    st.session_state.messages = [
        {"role": "model", "content": current_welcome}
    ]

if "is_typing" not in st.session_state:
    st.session_state.is_typing = False

# -------------------------------
# Configure Gemini API
# -------------------------------
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("❌ GEMINI_API_KEY not found in .env file!")
    st.stop()

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
except Exception as e:
    st.error(f"❌ Gemini setup failed: {e}")
    st.stop()

# -------------------------------
# Display Chat History
# -------------------------------
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"<div class='user-msg'>{msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"""
    <div class='bot-msg-container'>
        <div class='bot-avatar'>
            <img src="https://raw.githubusercontent.com/ymteoh/fyp-finance/main/logo_circle.png" alt="AI Assistant">
        </div>
        <div class='bot-msg'>{msg['content']}</div>
    </div>
""", unsafe_allow_html=True)

if st.session_state.is_typing:
    st.markdown("""
        <div class='bot-msg-container'>
            <div class='bot-avatar'>
                <img src="https://i.ibb.co/F4B77jC0/logo.png" alt="AI Assistant">
            </div>
            <div class='typing-indicator'>
                <div class='typing-dot'></div>
                <div class='typing-dot'></div>
                <div class='typing-dot'></div>
                <span>Thinking...</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# -------------------------------
# User Input & Smart Routing 
# -------------------------------
user_input = st.chat_input("Ask about your finances...")

if user_input:
    user_input_clean = user_input.strip()
    if user_input_clean:
        st.session_state.messages.append({"role": "user", "content": user_input_clean})
        st.session_state.is_typing = True
        st.rerun()

# Process response with intelligent routing
if st.session_state.is_typing and st.session_state.messages[-1]["role"] == "user":
    user_query = st.session_state.messages[-1]["content"].lower()
    bot_reply = None

    # 1. ACTION PLANS (highest priority)
    if any(k in user_query for k in ["action plan", "what to do", "how to fix", "help me", "steps", "advice"]):
        if any(kw in user_query for kw in ["trend", "increasing", "month over month", "mom"]):
            trend_report = get_mom_trend(df, exchange_rate, currency_symbol)
            if "increasing" in trend_report:
                bot_reply = get_mom_action_plan(user_query, df, exchange_rate, currency_symbol)
            else:
                bot_reply = "Your spending trend is stable or decreasing—great job! No action needed."
        elif any(kw in user_query for kw in ["cash flow", "volatile", "stability", "consistent"]):
            stability_report = get_cash_flow_stability(df, exchange_rate, currency_symbol)
            if "Volatile" in stability_report or "Highly Volatile" in stability_report:
                bot_reply = get_cash_flow_action_plan(user_query, df, exchange_rate, currency_symbol)
            else:
                bot_reply = "Your cash flow is stable—excellent! Keep maintaining your buffer."
        else:
            bot_reply = get_alert_action_plan(user_query, df, exchange_rate, currency_symbol)

    # 2. SPECIALIZED REPORTS (context-aware)
    elif any(k in user_query for k in [
        "cash flow", "consistent", "stability", "volatile", "steady income",
        "how consistent", "income stability", "expense stability", "volatility",
        "financial rollercoaster", "money up and down", "income stable", "stable"
    ]):
        bot_reply = get_cash_flow_stability(df, exchange_rate, currency_symbol)

    # Monthly income
    elif any(k in user_query for k in [
        "earnings this month", "income this month", "this month income", "monthly income",
        "show me my earnings this month", "current income", "money this month"
    ]):
        bot_reply = get_total_income(df, exchange_rate, currency_symbol, monthly=True)

    # Monthly balance
    elif any(k in user_query for k in [
        "profit or loss this month", "am i in profit this month", "monthly profit",
        "this month balance", "net this month", "balance this month", "current balance"
    ]):
        bot_reply = get_net_balance(df, exchange_rate, currency_symbol, monthly=True)

    # Generic income
    elif any(k in user_query for k in ["income", "earnings", "salary", "revenue", "money did i make", "how much did i earn", "total earnings", "made money"]):
        bot_reply = get_total_income(df, exchange_rate, currency_symbol)

    # Generic balance
    elif any(k in user_query for k in ["balance", "net", "profit", "loss", "profit or loss", "am i in", "bottom line", "net position"]):
        bot_reply = get_net_balance(df, exchange_rate, currency_symbol)

    # 3. STANDARD REPORTS (broad keywords)
    elif any(k in user_query for k in ["alert", "overspend", "warning"]):
        bot_reply = get_spending_alert(df, exchange_rate, currency_symbol)

    elif "detailed tips for" in user_query:
        bot_reply = get_budget_detailed_tips(user_query, df, exchange_rate, currency_symbol)

    elif any(k in user_query for k in ["tip", "budget", "save money", "reduce", "cut"]):
        bot_reply = get_budget_tip(df, exchange_rate, currency_symbol)

    elif any(k in user_query for k in ["forecast", "next month", "future", "predict"]):
        bot_reply = get_forecast_summary(df, exchange_rate, currency_symbol)

    elif any(k in user_query for k in ["last 5", "recent", "latest transactions"]):
        bot_reply = get_last_5_transactions(df, exchange_rate, currency_symbol)

    elif any(k in user_query for k in ["top", "highest", "most spent", "biggest expense"]):
        bot_reply = get_top_expense_category(df, exchange_rate, currency_symbol)

    elif any(k in user_query for k in ["recurring", "subscription", "auto-pay", "monthly bill"]):
        bot_reply = get_recurring_audit(df, exchange_rate, currency_symbol)

    elif any(k in user_query for k in ["savings", "save", "buffer", "emergency fund", "financial health"]):
        bot_reply = get_savings_health(df, exchange_rate, currency_symbol)

    elif any(k in user_query for k in ["trend", "increasing", "decreasing", "month over month", "mom"]):
        bot_reply = get_mom_trend(df, exchange_rate, currency_symbol)

    # 4. FULL AI FALLBACK
    if bot_reply is None:
        try:
            response = model.generate_content(st.session_state.messages[-1]["content"])
            bot_reply = response.text
        except Exception as e:
            bot_reply = f"Sorry, I had trouble processing that. Error: {str(e)[:50]}..."

    st.session_state.messages.append({"role": "model", "content": bot_reply})
    st.session_state.is_typing = False
    st.rerun()

st.markdown("<div style='margin: 30px 0 20px 0;'></div>", unsafe_allow_html=True)

# -------------------------------
# Quick Suggestions 
# -------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("Show last 5 transactions", use_container_width=True):
        response = get_last_5_transactions(df, exchange_rate, currency_symbol)
        st.session_state.messages.append({"role": "user", "content": "Show last 5 transactions"})
        st.session_state.messages.append({"role": "model", "content": response})
        st.rerun()

with col2:
    if st.button("Total income?", use_container_width=True):
        response = get_total_income(df, exchange_rate, currency_symbol)
        st.session_state.messages.append({"role": "user", "content": "Total income?"})
        st.session_state.messages.append({"role": "model", "content": response})
        st.rerun()

with col3:
    if st.button("What's my net balance?", use_container_width=True):
        response = get_net_balance(df, exchange_rate, currency_symbol)
        st.session_state.messages.append({"role": "user", "content": "What's my balance?"})
        st.session_state.messages.append({"role": "model", "content": response})
        st.rerun()

with col4:
    if st.button("Top expense category?", use_container_width=True):
        response = get_top_expense_category(df, exchange_rate, currency_symbol)
        st.session_state.messages.append({"role": "user", "content": "Top expense category?"})
        st.session_state.messages.append({"role": "model", "content": response})
        st.rerun()

# -------------------------------
# Footer
# -------------------------------
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f"<p style='text-align:center; font-size:0.9em; color:#c2185b;'>© 2025 Financial Assistant | Currency: {selected_currency} ({currency_symbol}) | Powered by AI</p>",
    unsafe_allow_html=True
)


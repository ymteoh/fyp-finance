# pages/trends.py
# FINAL VERSION — Multi-Currency Support + Sync with Dashboard

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sqlite3
import os
import requests
from datetime import datetime
from prophet import Prophet
import warnings
warnings.filterwarnings("ignore")

# -------------------------------
# Shared Currency Configuration
# -------------------------------
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

# -------------------------------
# Login Check
# -------------------------------
if not st.session_state.get("logged_in", False):
    st.error("Please log in first.")
    if st.button("Go to Login"):
        st.switch_page("app.py")
    st.stop()

# -------------------------------
# Read selected currency from session (set in dashboard.py)
# -------------------------------
selected_currency = st.session_state.get("selected_currency", "MYR")
exchange_rate = get_exchange_rate("MYR", selected_currency)
currency_symbol = currency_symbol_map.get(selected_currency, selected_currency + " ")

st.set_page_config(
    page_title=f"AI Forecast ({selected_currency})",
    page_icon="logo_circle.png",
    layout="wide"
)

# -------------------------------
# Sidebar
# -------------------------------
st.sidebar.markdown(f"**Currency:** {selected_currency} ({currency_symbol})")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.switch_page("app.py")

# -------------------------------
# Styling
# -------------------------------
st.markdown(f"""
<style>
    .main {{ 
        background: white; 
        padding: 20px; 
        font-family: 'Segoe UI', 'Inter', sans-serif; 
        margin-top: -30px;
    }}
    h1 {{ 
        color: black; 
        text-align: center; 
        font-weight: 700; 
    }}
    .original-subtitle {{
        text-align: center; 
        color: #c2185b; 
        font-size: 0.9em;
    }}
    .card {{
        background: white;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.04);
        margin-bottom: 24px;
    }}
    hr {{ border-color: #e2e8f0; margin: 1.5rem 0; }}
</style>
""", unsafe_allow_html=True)

# -------------------------------
# Header
# -------------------------------
col_back, col_title, col_spacer = st.columns([0.5, 4, 0.5])
with col_back:
    if st.button("←", help="Return to Dashboard", type="secondary"):
        st.switch_page("pages/dashboard.py")
with col_title:
    st.markdown("<h1>📈 Trend & Prediction</h1>", unsafe_allow_html=True)
    st.markdown('<p class="original-subtitle">Predict your financial trends with AI</p>', unsafe_allow_html=True)

# -------------------------------
# DATA LOADING (WITH CURRENCY AWARENESS)
# -------------------------------
@st.cache_data(ttl=3600, show_spinner="Running AI model ...")
def get_forecast_with_history(selected_currency="MYR"):
    exchange_rate = get_exchange_rate("MYR", selected_currency)
    conn = sqlite3.connect("finance.db")
    df = pd.read_sql_query("SELECT date, amount, type, category FROM transactions", conn)
    conn.close()

    df['Date'] = pd.to_datetime(df['date'], errors='coerce')
    df['Amount'] = pd.to_numeric(df['amount'], errors='coerce') * exchange_rate
    df['Type'] = df['type'].str.strip().str.upper()
    df['Category'] = df['category'].str.strip().str.title()
    df = df.dropna(subset=['Date', 'Amount', 'Type', 'Category'])
    df = df[df['Type'].isin(['INCOME', 'EXPENSE'])]

    HORIZONS = {
        "4 Days": (4, 'D'), "4 Weeks": (4, 'W'),
        "2 Months": (2, 'M'), "4 Months": (4, 'M'), "1 Year": (12, 'M')
    }

    results = {}
    for label, (periods, freq) in HORIZONS.items():
        for typ in ['INCOME', 'EXPENSE']:
            data = df[df['Type'] == typ].copy()
            data['Period'] = data['Date'].dt.to_period(freq).dt.to_timestamp()

            if typ == 'INCOME':
                cats = ['Total Income'] + sorted(data['Category'].unique())
            else:
                cats = sorted(data['Category'].unique())

            for cat in cats:
                if cat == 'Total Income':
                    series = data.groupby('Period')['Amount'].sum()
                else:
                    series = data[data['Category'] == cat].groupby('Period')['Amount'].sum()

                hist_df = series.reset_index()
                hist_df.columns = ['ds', 'y']
                hist_df = hist_df.sort_values('ds')

                if len(hist_df) < 3:
                    continue

                m = Prophet(yearly_seasonality=(freq in ['D','W']), weekly_seasonality=(freq=='D'),
                            seasonality_mode='additive', interval_width=0.8)
                m.fit(hist_df)

                future = m.make_future_dataframe(periods=periods, freq=freq)
                forecast = m.predict(future)
                pred = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods).copy()

                last_4_actual = hist_df.tail(4).copy()

                pred['ds'] = pred['ds'].dt.strftime('%Y-%m-%d' if freq in ['D','W'] else '%b %Y')
                last_4_actual['ds'] = last_4_actual['ds'].dt.strftime('%Y-%m-%d' if freq in ['D','W'] else '%b %Y')

                key = f"{label}_{typ}_{cat}"
                results[key] = {
                    'forecast': pred.round(0),
                    'history': last_4_actual.round(0),
                    'last_actual_total': hist_df['y'].iloc[-periods:].sum() if len(hist_df) >= periods else hist_df['y'].sum(),
                    'category': cat
                }
    return results

@st.cache_data(ttl=3600)
def load_raw_transactions(selected_currency="MYR"):
    exchange_rate = get_exchange_rate("MYR", selected_currency)
    conn = sqlite3.connect("finance.db")
    df = pd.read_sql_query("SELECT date, amount, type, category FROM transactions", conn)
    conn.close()
    
    df['Date'] = pd.to_datetime(df['date'], errors='coerce')
    df['Amount'] = pd.to_numeric(df['amount'], errors='coerce') * exchange_rate
    df['Type'] = df['type'].str.strip().str.upper()
    df['Category'] = df['category'].str.strip().str.title()
    df = df.dropna(subset=['Date', 'Amount', 'Type', 'Category'])
    df = df[df['Type'].isin(['INCOME', 'EXPENSE'])]
    return df

# Load data — PASS CURRENCY TO CACHE KEY
data = get_forecast_with_history(selected_currency=selected_currency)
data_source = load_raw_transactions(selected_currency=selected_currency)

# -------------------------------
# Forecast Selector
# -------------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.markdown("### 🔮 Forecast Horizon")
    horizon = st.selectbox("Select Horizon", ["4 Days", "4 Weeks", "2 Months", "4 Months", "1 Year"], index=2)
with col2:
    st.markdown("### 🎯 Forecast Target")
    options = [v['category'] for k, v in data.items() if horizon in k]
    options = sorted(set(options))
    selected = st.selectbox("Show Forecast For", options if options else ["Total Income"])
st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------
# Retrieve Selected Forecast
# -------------------------------
selected_key = None
for k, v in data.items():
    if horizon in k and v['category'] == selected:
        selected_key = k
        break

if not selected_key:
    st.error("No data for this selection.")
    st.stop()

forecast_df = data[selected_key]['forecast']
history_df = data[selected_key]['history']
last_actual_total = data[selected_key]['last_actual_total']

forecast_df['Date'] = pd.to_datetime(forecast_df['ds'])
history_df['Date'] = pd.to_datetime(history_df['ds'])

total_pred = forecast_df['yhat'].sum()
lower = forecast_df['yhat_lower'].sum()
upper = forecast_df['yhat_upper'].sum()
change_pct = ((total_pred - last_actual_total) / last_actual_total * 100) if last_actual_total > 0 else 0

# -------------------------------
# Forecast Chart
# -------------------------------
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=history_df['Date'], y=history_df['y'],
    mode='lines+markers',
    name='Last 4 Actual',
    line=dict(color='#4f46e5', width=3),
    marker=dict(size=8, color='#4f46e5')
))

last_hist_date = history_df['Date'].iloc[-1]
last_hist_value = history_df['y'].iloc[-1]

connected_forecast_x = [last_hist_date] + forecast_df['Date'].tolist()
connected_forecast_y = [last_hist_value] + forecast_df['yhat'].tolist()

fig.add_trace(go.Scatter(
    x=connected_forecast_x,
    y=connected_forecast_y,
    mode='lines+markers',
    name='AI Forecast',
    line=dict(color='#0d9488', width=3, dash='dot'),
    marker=dict(size=8, symbol='diamond', color='#0d9488')
))

fig.add_trace(go.Scatter(
    x=forecast_df['Date'].tolist() + forecast_df['Date'].tolist()[::-1],
    y=forecast_df['yhat_upper'].tolist() + forecast_df['yhat_lower'].tolist()[::-1],
    fill='toself',
    fillcolor='rgba(13, 148, 136, 0.12)',
    line=dict(color='rgba(0,0,0,0)'),
    name='80% Confidence'
))

fig.update_layout(
    title=f"{selected} • {horizon} Forecast",
    xaxis_title="", 
    yaxis_title=f"Amount ({currency_symbol})",
    hovermode='x unified',
    height=520,
    template="simple_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
    hoverlabel=dict(bgcolor="white", font_size=13, font_family="Segoe UI"),
    xaxis=dict(showgrid=True, gridcolor='#f1f5f9'),
    yaxis=dict(showgrid=True, gridcolor='#f1f5f9', tickprefix=f"{currency_symbol} ")
)

st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# Metrics
# -------------------------------
st.markdown("### Key Insights")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Predicted Total", f"{currency_symbol} {total_pred:,.0f}")
with col2:
    st.metric("vs Previous Period", f"{change_pct:+.1f}%", 
              delta=f"{change_pct:+.1f}%" if change_pct != 0 else None,
              delta_color="normal" if change_pct >= 0 else "inverse")
with col3:
    st.metric("80% Confidence Range", f"{currency_symbol} {lower:,.0f} – {upper:,.0f}")

# -------------------------------
# Future Predictions Table
# -------------------------------
st.markdown("#### Future Predictions")
table = forecast_df[['ds', 'yhat']].copy()
table.columns = ['Date', 'Predicted']
table['Predicted'] = table['Predicted'].astype(int)

styled_table = table.style.format({"Predicted": f"{currency_symbol} " + "{:,}"}).set_properties(**{
    'background-color': 'white',
    'color': '#0f0f0f',
    'border': '1px solid #f8bbd0',
    'text-align': 'center'
}).set_table_styles([
    {'selector': 'th', 'props': [('background-color', '#fce4ec'), ('color', '#d81b60'), ('font-weight', '600')]},
    {'selector': 'td', 'props': [('padding', '12px')]},
])

st.dataframe(styled_table, use_container_width=True, hide_index=True)

# -------------------------------
# Help Expander
# -------------------------------
with st.expander("🔍 How to interpret this forecast"):
    st.markdown(f"""
    - **Solid blue line**: Last 4 actual historical values  
    - **Dotted teal line**: AI-predicted future values  
    - **Light teal shaded area**: 80% confidence interval  
    - All values shown in **{selected_currency} ({currency_symbol})**
    """)

# -------------------------------
# Historical Trend
# -------------------------------
st.markdown("---")
st.subheader("Historical Trend")

trend_period = st.select_slider(
    "View Historical Data",
    options=["3M", "6M", "1Y", "2Y", "All"],
    value="1Y"
)

cutoff_map = {"3M": 90, "6M": 180, "1Y": 365, "2Y": 730, "All": 9999}
days = cutoff_map[trend_period]
hist_data = data_source[data_source['Date'] >= data_source['Date'].max() - pd.Timedelta(days=days)]

if selected.startswith("Total "):
    hist_agg = hist_data.groupby(hist_data['Date'].dt.to_period('M').dt.to_timestamp())['Amount'].sum().reset_index()
    title = f"{selected} Trend"
else:
    hist_agg = hist_data[hist_data['Category'] == selected]
    hist_agg = hist_agg.groupby(hist_agg['Date'].dt.to_period('M').dt.to_timestamp())['Amount'].sum().reset_index()
    title = f"{selected} Monthly Trend"

if not hist_agg.empty:
    hist_agg['Month'] = hist_agg['Date'].dt.strftime('%b %Y')
    fig_trend = px.bar(
        hist_agg, x='Date', y='Amount',
        title=title,
        color_discrete_sequence=['#636efa'],
        hover_data={'Amount': ':,.0f'},
        custom_data=['Month']
    )
    fig_trend.add_scatter(
        x=hist_agg['Date'], y=hist_agg['Amount'],
        mode='lines+markers', name='Trend',
        line=dict(color='#61dafb', width=2),
        marker=dict(color='#61dafb', size=6),
        hovertemplate=f'Trend: {currency_symbol} %{{y:,.0f}}<extra></extra>'
    )
    fig_trend.update_layout(
        height=400,
        xaxis_title="",
        yaxis_title=currency_symbol,
        hovermode='x unified',
        xaxis=dict(showgrid=True, gridcolor='#f1f5f9', tickformat='%b %Y'),
        yaxis=dict(showgrid=True, gridcolor='#f1f5f9', tickprefix=f"{currency_symbol} ")
    )
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.warning("No historical data in selected period.")

# -------------------------------
# Refresh Button
# -------------------------------
col_r1, col_r2 = st.columns([1, 5])
with col_r1:
    if st.button("🔄 Refresh", type="secondary"):
        st.cache_data.clear()
        st.rerun()
with col_r2:
    st.caption("Clears cached data and reloads all forecasts")

# -------------------------------
# AI Insight
# -------------------------------
# -------------------------------
# AI Insight (Refined Original Style)
# -------------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### 🤖 AI Insight Summary")

if len(history_df) > 0:
    last_actual_val = history_df['y'].iloc[-1]
    next_pred_val = forecast_df['yhat'].iloc[0]
    
    if next_pred_val > last_actual_val:
        trend = "increase"
    elif next_pred_val < last_actual_val:
        trend = "decrease"
    else:
        trend = "remain stable"

    # Safe uncertainty calculation
    if next_pred_val != 0:
        uncertainty = (forecast_df['yhat_upper'].iloc[0] - forecast_df['yhat_lower'].iloc[0]) / abs(next_pred_val)
    else:
        uncertainty = 0.0

    if uncertainty < 0.1:
        unc = "low"
        note = "highly consistent"
    elif uncertainty < 0.25:
        unc = "moderate"
        note = "reasonably predictable"
    else:
        unc = "high"
        note = "volatile"

    if selected == "Total Income":
        line1 = f"Total income is projected to **{trend}** over the next **{horizon.lower()}**."
        line2 = f"With **{unc}** uncertainty, the forecast is **{note}**."
    else:
        line1 = f"**{selected}** is projected to **{trend}** over the next **{horizon.lower()}**."
        line2 = f"The **{unc}** uncertainty indicates **{note}** spending behavior."

    st.info(f"{line1}\n\n{line2}")

else:
    st.info("Insufficient data to generate an AI insight.")

st.markdown('</div>', unsafe_allow_html=True)
# -------------------------------
# Footer
# -------------------------------
st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown(
    f"<p style='text-align:center; font-size:0.9em; color:#c2185b;'>"
    f"AI Forecast • Currency: {selected_currency} • Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    "</p>",
    unsafe_allow_html=True
)

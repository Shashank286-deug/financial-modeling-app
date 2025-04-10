import streamlit as st
import requests
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime
import openpyxl
from openpyxl.chart import BarChart, Reference
import yfinance as yf
from tradingview_ta import TA_Handler, Interval, Exchange

# Load FMP API key securely from Streamlit secrets
FMP_API_KEY = st.secrets["FMP_API_KEY"]

st.set_page_config(page_title="Financial Dashboard", layout="wide")
st.title("📊 Financial Model & Valuation Dashboard")

# Sidebar
ticker = st.sidebar.text_input("Enter Ticker (e.g., AAPL, MSFT)", value="AAPL")
view_mode = st.sidebar.radio("Select Dashboard Mode", ["📊 Summary View", "🔍 Deep Dive View"])

# Function to fetch financial data from FMP
@st.cache_data(ttl=3600)
def get_fmp_financials(ticker):
    base_url = "https://financialmodelingprep.com/api/v3"
    suffix = f"?apikey={FMP_API_KEY}"

    endpoints = {
        "profile": f"/profile/{ticker}{suffix}",
        "income": f"/income-statement/{ticker}?limit=5{suffix}",
        "balance": f"/balance-sheet-statement/{ticker}?limit=5{suffix}",
        "cashflow": f"/cash-flow-statement/{ticker}?limit=5{suffix}",
        "ratios": f"/ratios-ttm/{ticker}{suffix}",
        "dcf": f"/discounted-cash-flow/{ticker}{suffix}",
        "price": f"/historical-price-full/{ticker}?serietype=line&timeseries=365{suffix}"
    }

    data = {}
    for key, endpoint in endpoints.items():
        r = requests.get(base_url + endpoint)
        if r.status_code == 200:
            data[key] = r.json()
        else:
            data[key] = []
    return data

# Fallback using yfinance
@st.cache_data(ttl=3600)
def get_yahoo_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        return hist.reset_index()
    except:
        return pd.DataFrame()

# Fetch Button
if st.button("📥 Fetch Financials"):
    with st.spinner("Loading data from FMP..."):
        data = get_fmp_financials(ticker)

        # Company Summary Section
        profile = data.get("profile", [])
        if profile and isinstance(profile, list):
            company = profile[0]
            name = company.get("companyName", "N/A")
            industry = company.get("industry", "N/A")
            ipo = company.get("ipoDate", "N/A")
            st.markdown(f"### 🏢 {ticker.upper()} ({name})")
            st.markdown(f"**Industry:** {industry}  ")
            st.markdown(f"**Founded (IPO):** {ipo}")

        # Dashboard Toggle Handling
        if view_mode == "📊 Summary View":
            st.info("Summary View shows only key insights.")

        # Display Key Ratios
        st.subheader("📌 Key Ratios")
        ratios = data['ratios']
        if isinstance(ratios, list) and len(ratios) > 0:
            ratio_data = ratios[0]
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                val = ratio_data.get("peRatioTTM")
                st.metric("P/E Ratio", f"{val:.2f}" if val else "-", delta="")
            with col2:
                val = ratio_data.get("returnOnEquityTTM")
                st.metric("ROE", f"{val:.2f}" if val else "-", delta="")
            with col3:
                val = ratio_data.get("returnOnAssetsTTM")
                st.metric("ROA", f"{val:.2f}" if val else "-", delta="")
            with col4:
                val = ratio_data.get("debtEquityRatioTTM")
                st.metric("Debt/Equity", f"{val:.2f}" if val else "-", delta="")
            with col5:
                val = ratio_data.get("epsTTM")
                st.metric("EPS", f"{val:.2f}" if val else "-", delta="")
        else:
            st.warning("Ratio data not available or in unexpected format.")

        if view_mode == "🔍 Deep Dive View":
            # DCF Valuation
            st.subheader("📈 DCF Valuation")
            if data['dcf']:
                try:
                    dcf_value = float(data['dcf'][0]['dcf'])
                    price = float(data['dcf'][0]['Stock Price'])
                    st.metric("DCF Value", f"${dcf_value:.2f}", delta=f"Market Price: ${price:.2f}")
                except:
                    st.warning("DCF data parsing error")

            # Multi-year Comparisons
            st.subheader("🗂 Multi-Year Financials")
            for name, d in [
                ("Income Statement", data['income']),
                ("Balance Sheet", data['balance']),
                ("Cash Flow", data['cashflow'])
            ]:
                if isinstance(d, list) and d:
                    df = pd.DataFrame(d)
                    if 'date' in df.columns:
                        df.set_index("date", inplace=True)
                    st.markdown(f"### {name}")
                    st.dataframe(df.style.format(na_rep="-"), use_container_width=True)
                else:
                    st.warning(f"{name} not available from FMP.")

            # Bar Chart - Total Revenue
            st.subheader("📊 Revenue Trend")
            if data['income']:
                df_rev = pd.DataFrame(data['income'])
                if 'revenue' in df_rev.columns:
                    df_rev = df_rev[['date', 'revenue']].dropna()
                    df_rev['revenue'] = pd.to_numeric(df_rev['revenue'])
                    fig = px.bar(df_rev.sort_values(by='date'), x='date', y='revenue', title="Revenue Over Time")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Revenue data not available.")

            # Historical Stock Price Line Chart
            st.subheader("📉 Historical Stock Price")
            if data['price'] and 'historical' in data['price']:
                df_price = pd.DataFrame(data['price']['historical'])
                df_price['date'] = pd.to_datetime(df_price['date'])
                fig_line = px.line(df_price, x='date', y='close', title=f"{ticker} Stock Price")
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.warning("FMP stock price data not available. Trying Yahoo Finance...")
                yahoo_df = get_yahoo_data(ticker)
                if not yahoo_df.empty:
                    fig_yahoo = px.line(yahoo_df, x='Date', y='Close', title=f"{ticker} Stock Price (Yahoo Finance)")
                    st.plotly_chart(fig_yahoo, use_container_width=True)
                else:
                    st.error("Could not fetch stock data from Yahoo Finance either.")

            # Excel Export of Full Financials
            st.subheader("📤 Export to Excel")
            with BytesIO() as buffer:
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    pd.DataFrame(data['income']).to_excel(writer, sheet_name="Income", index=False)
                    pd.DataFrame(data['balance']).to_excel(writer, sheet_name="Balance", index=False)
                    pd.DataFrame(data['cashflow']).to_excel(writer, sheet_name="Cash Flow", index=False)
                    pd.DataFrame([ratios[0]] if isinstance(ratios, list) and ratios else [{}]).to_excel(writer, sheet_name="Ratios", index=False)
                st.download_button("💾 Download Full Financials", buffer.getvalue(), file_name=f"{ticker}_financials.xlsx")

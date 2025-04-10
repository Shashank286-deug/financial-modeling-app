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

# Function to fetch financial data from FMP
@st.cache_data(ttl=3600)
def get_fmp_financials(ticker):
    base_url = "https://financialmodelingprep.com/api/v3"
    suffix = f"?apikey={FMP_API_KEY}"

    endpoints = {
        "income": f"/income-statement/{ticker}?limit=5{suffix}",
        "balance": f"/balance-sheet-statement/{ticker}?limit=5{suffix}",
        "cashflow": f"/cash-flow-statement/{ticker}?limit=5{suffix}",
        "ratios": f"/ratios-ttm/{ticker}{suffix}",
        "dcf": f"/discounted-cash-flow/{ticker}{suffix}",
        "price": f"/historical-price-full/{ticker}?serietype=line&timeseries=365{suffix}",
        "profile": f"/profile/{ticker}{suffix}"
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

# CAGR Calculation
def calculate_cagr(start_value, end_value, periods):
    if start_value <= 0 or end_value <= 0 or periods <= 0:
        return float('nan')
    return (end_value / start_value) ** (1 / periods) - 1

# Fetch Button
if st.button("📥 Fetch Financials"):
    with st.spinner("Loading data from FMP..."):
        data = get_fmp_financials(ticker)

        # Display Company Name and Industry Info
        if data['profile']:
            info = data['profile'][0]
            st.subheader(f"{ticker} ({info.get('companyName')})")
            st.caption(f"Industry: {info.get('industry')} | Sector: {info.get('sector')} | IPO Year: {info.get('ipoDate', '')[:4]}")

        # Display Key Ratios
        st.subheader("📌 Key Ratios")
        ratios = data['ratios']
        if isinstance(ratios, list) and len(ratios) > 0:
            ratio_data = ratios[0]
            formatted_ratios = {
                "P/E Ratio": ratio_data.get("peRatioTTM", float('nan')),
                "ROE": ratio_data.get("returnOnEquityTTM", float('nan')),
                "ROA": ratio_data.get("returnOnAssetsTTM", float('nan')),
                "Debt/Equity": ratio_data.get("debtEquityRatioTTM", float('nan')),
                "EPS": ratio_data.get("epsTTM", float('nan'))
            }
            ratios_df = pd.DataFrame([formatted_ratios])
            st.dataframe(ratios_df.style.format({col: "{:.2f}" for col in ratios_df.columns}), use_container_width=True)
        else:
            st.warning("Ratio data not available or in unexpected format.")

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

        # EPS Growth Trend
        st.subheader("📈 EPS Growth Over Time")
        if data['income']:
            df_eps = pd.DataFrame(data['income'])
            if 'eps' in df_eps.columns:
                df_eps = df_eps[['date', 'eps']].dropna()
                df_eps['eps'] = pd.to_numeric(df_eps['eps'])
                fig_eps = px.line(df_eps.sort_values('date'), x='date', y='eps', title="EPS Over Time")
                st.plotly_chart(fig_eps, use_container_width=True)

        # Sector Comparison with Peers
        st.subheader("🏢 Industry Benchmarking")
        peer_tickers = st.multiselect("Select Peers for Comparison", ["AAPL", "MSFT", "GOOGL", "AMZN", "META"], default=["AAPL", "MSFT"])
        metric = st.selectbox("Choose Metric", ["EPS", "Return on Equity", "Return on Assets"])
        sector_data = []
        for peer in peer_tickers:
            peer_data = get_fmp_financials(peer)
            try:
                ratio = peer_data['ratios'][0]
                val = ratio.get("epsTTM" if metric == "EPS" else ("returnOnEquityTTM" if metric == "Return on Equity" else "returnOnAssetsTTM"), float('nan'))
                sector_data.append({"Ticker": peer, metric: val})
            except:
                continue

        if sector_data:
            df_sector = pd.DataFrame(sector_data)
            fig_sector = px.bar(df_sector, x='Ticker', y=metric, color='Ticker', title=f"Sector Comparison by {metric}")
            st.plotly_chart(fig_sector, use_container_width=True)

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

        # Export to Excel
        st.subheader("📤 Export to Excel")
        with BytesIO() as buffer:
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                pd.DataFrame(data['income']).to_excel(writer, sheet_name="Income", index=False)
                pd.DataFrame(data['balance']).to_excel(writer, sheet_name="Balance", index=False)
                pd.DataFrame(data['cashflow']).to_excel(writer, sheet_name="Cash Flow", index=False)
                pd.DataFrame([ratios[0]] if isinstance(ratios, list) and ratios else [{}]).to_excel(writer, sheet_name="Ratios", index=False)
            st.download_button("💾 Download Full Financials", buffer.getvalue(), file_name=f"{ticker}_financials.xlsx")

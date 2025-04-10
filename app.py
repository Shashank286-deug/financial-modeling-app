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
from tradingview_ta import TA_Handler, Interval, Exchange

# Load FMP API key securely from Streamlit secrets
FMP_API_KEY = st.secrets["FMP_API_KEY"]

st.set_page_config(page_title="Financial Dashboard", layout="wide")
st.title("📊 Financial Model & Valuation Dashboard")

# Sidebar
st.sidebar.header("Settings")
ticker_list = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
ticker_input = st.sidebar.text_input("Enter Ticker Symbol", value="AAPL").upper()
ticker = ticker_input if ticker_input else "AAPL"

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

# Function to fetch TradingView data
def get_tradingview_analysis(ticker):
    try:
        handler = TA_Handler(
            symbol=ticker,
            screener="america",
            exchange="NASDAQ",
            interval=Interval.INTERVAL_1_DAY
        )
        return handler.get_analysis()
    except Exception as e:
        return str(e)

# Fetch Button
if st.button("📥 Fetch Financials"):
    with st.spinner("Loading data from FMP..."):
        data = get_fmp_financials(ticker)

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
                df.set_index("date", inplace=True)
                st.markdown(f"### {name}")
                st.dataframe(df.style.format(na_rep="-"), use_container_width=True)

        # Bar Chart - Total Revenue
        st.subheader("📊 Revenue Trend")
        if data['income']:
            df_rev = pd.DataFrame(data['income'])
            df_rev = df_rev[['date', 'revenue']].dropna()
            df_rev['revenue'] = pd.to_numeric(df_rev['revenue'])
            fig = px.bar(df_rev.sort_values(by='date'), x='date', y='revenue', title="Revenue Over Time")
            st.plotly_chart(fig, use_container_width=True)

        # Historical Stock Price Line Chart
        st.subheader("📉 Historical Stock Price")
        if data['price'] and 'historical' in data['price']:
            df_price = pd.DataFrame(data['price']['historical'])
            df_price['date'] = pd.to_datetime(df_price['date'])
            fig_line = px.line(df_price, x='date', y='close', title=f"{ticker} Stock Price")
            st.plotly_chart(fig_line, use_container_width=True)

        # TradingView Analysis
        st.subheader("🔍 TradingView Technical Summary")
        tv_analysis = get_tradingview_analysis(ticker)
        if isinstance(tv_analysis, str):
            st.error(f"TradingView Error: {tv_analysis}")
        else:
            st.json(tv_analysis.summary)
            st.json(tv_analysis.moving_averages)

        # Excel Export of Full Financials
        st.subheader("📤 Export to Excel")
        with BytesIO() as buffer:
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                pd.DataFrame(data['income']).to_excel(writer, sheet_name="Income", index=False)
                pd.DataFrame(data['balance']).to_excel(writer, sheet_name="Balance", index=False)
                pd.DataFrame(data['cashflow']).to_excel(writer, sheet_name="Cash Flow", index=False)
                pd.DataFrame([ratios[0]] if isinstance(ratios, list) and ratios else [{}]).to_excel(writer, sheet_name="Ratios", index=False)
            st.download_button("💾 Download Full Financials", buffer.getvalue(), file_name=f"{ticker}_financials.xlsx")

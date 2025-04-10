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
benchmark_ticker = st.sidebar.text_input("Enter Benchmark Ticker (optional)", value="SPY")

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
    try:
        return ((end_value / start_value) ** (1 / periods)) - 1
    except:
        return None

# Fetch Button
if st.button("📥 Fetch Financials"):
    with st.spinner("Loading data from FMP..."):
        data = get_fmp_financials(ticker)
        benchmark_data = get_fmp_financials(benchmark_ticker) if benchmark_ticker else None

        st.subheader(f"📌 Company Overview")
        if data['profile']:
            profile = data['profile'][0]
            st.markdown(f"**{profile.get('companyName', '')}**  ")
            st.markdown(f"Industry: {profile.get('industry', '-')}, Sector: {profile.get('sector', '-')}, IPO Year: {profile.get('ipoDate', '-')}")

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

        # ROI and EPS Sector Comparison
        st.subheader("📊 Sector Comparison: ROI & EPS")
        if benchmark_data and benchmark_data['ratios']:
            ticker_ratios = data['ratios'][0]
            bench_ratios = benchmark_data['ratios'][0]
            comp_df = pd.DataFrame({
                "Metric": ["ROI", "EPS"],
                ticker: [ticker_ratios.get("returnOnInvestmentTTM", 0), ticker_ratios.get("epsTTM", 0)],
                benchmark_ticker: [bench_ratios.get("returnOnInvestmentTTM", 0), bench_ratios.get("epsTTM", 0)]
            })
            comp_fig = px.bar(comp_df, x="Metric", y=[ticker, benchmark_ticker], barmode='group', title="ROI and EPS Comparison")
            st.plotly_chart(comp_fig, use_container_width=True)

        # Historical Stock Price Line Chart
        st.subheader("📉 Historical Stock Price")
        if data['price'] and 'historical' in data['price']:
            df_price = pd.DataFrame(data['price']['historical'])
            df_price['date'] = pd.to_datetime(df_price['date'])
            fig_line = px.line(df_price, x='date', y='close', title=f"{ticker} Stock Price")
            st.plotly_chart(fig_line, use_container_width=True)

            # CAGR
            if len(df_price) >= 2:
                start_price = df_price.iloc[-1]['close']
                end_price = df_price.iloc[0]['close']
                years = (df_price.iloc[0]['date'] - df_price.iloc[-1]['date']).days / 365
                cagr = calculate_cagr(start_price, end_price, years)
                if cagr is not None:
                    st.metric("CAGR (Price)", f"{cagr*100:.2f}%")

        # Excel Export of Full Financials
        st.subheader("📤 Export to Excel")
        with BytesIO() as buffer:
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                pd.DataFrame(data['income']).to_excel(writer, sheet_name="Income", index=False)
                pd.DataFrame(data['balance']).to_excel(writer, sheet_name="Balance", index=False)
                pd.DataFrame(data['cashflow']).to_excel(writer, sheet_name="Cash Flow", index=False)
                pd.DataFrame([ratios[0]] if isinstance(ratios, list) and ratios else [{}]).to_excel(writer, sheet_name="Ratios", index=False)
            st.download_button("💾 Download Full Financials", buffer.getvalue(), file_name=f"{ticker}_financials.xlsx")

        # Image Export
        st.subheader("📸 Export Visuals")
        st.markdown("Use the Plotly chart menu (top-right corner of each chart) to download charts as PNG or PDF.")

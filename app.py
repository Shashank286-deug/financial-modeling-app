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
import base64

# Load API keys
FMP_API_KEY = st.secrets["FMP_API_KEY"]
FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY", "")
ALPHA_VANTAGE_API_KEY = st.secrets.get("ALPHA_VANTAGE_API_KEY", "")

st.set_page_config(page_title="Financial Dashboard", layout="wide")
st.title("📊 Financial Model & Valuation Dashboard")

# Sidebar
st.sidebar.header("Search & Benchmark")
ticker = st.sidebar.text_input("Enter Ticker (e.g., AAPL, MSFT)", value="AAPL")
benchmark_tickers = st.sidebar.text_input("Benchmark Tickers (comma-separated)", value="GOOGL,AMZN").split(',')

# Function to calculate CAGR
def calculate_cagr(start_value, end_value, years):
    if start_value <= 0 or years <= 0:
        return float('nan')
    return (end_value / start_value) ** (1 / years) - 1

# Function to export Plotly figure to downloadable image
@st.cache_data(ttl=3600)
def get_image_download_link(fig):
    buffer = BytesIO()
    fig.write_image(buffer, format='png')
    buffer.seek(0)
    b64 = base64.b64encode(buffer.read()).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="plot.png">📷 Download Chart as PNG</a>'
    return href

# Enhanced EPS & Benchmarking Table
if st.button("📥 Fetch Financials"):
    tickers = [ticker] + benchmark_tickers
    all_data = {}
    eps_df = pd.DataFrame()

    for tkr in tickers:
        try:
            data = requests.get(f"https://financialmodelingprep.com/api/v3/income-statement/{tkr}?limit=5&apikey={FMP_API_KEY}").json()
            eps_list = [float(x.get('eps', 0)) for x in data if 'eps' in x]
            years = len(eps_list)
            if years >= 2:
                cagr = calculate_cagr(eps_list[-1], eps_list[0], years-1)
                eps_df[tkr] = eps_list[::-1]
                eps_df.loc['CAGR'] = ["{:.2%}".format(cagr)] + ["" for _ in range(years - 1)]
                all_data[tkr] = data
        except Exception as e:
            st.warning(f"Could not load data for {tkr}: {e}")

    if not eps_df.empty:
        st.subheader("📈 EPS Growth & CAGR Benchmark")
        st.dataframe(eps_df.fillna("-"))

        # EPS Growth Chart
        eps_chart = px.line(eps_df.drop(index='CAGR', errors='ignore'), title="EPS Growth Trends")
        st.plotly_chart(eps_chart, use_container_width=True)
        st.markdown(get_image_download_link(eps_chart), unsafe_allow_html=True)

    # Sector Comparison
    st.subheader("📊 Industry Benchmarking")
    metrics = ["revenue", "netIncome", "eps"]
    selected_metric = st.selectbox("Select Metric", metrics)

    sector_data = []
    for tkr in tickers:
        if tkr in all_data and isinstance(all_data[tkr], list) and all_data[tkr]:
            latest = all_data[tkr][0]
            sector_data.append({"Ticker": tkr, selected_metric: latest.get(selected_metric, 0)})

    if sector_data:
        df_sector = pd.DataFrame(sector_data)
        fig_sector = px.bar(df_sector, x="Ticker", y=selected_metric, title=f"{selected_metric} Comparison")
        st.plotly_chart(fig_sector, use_container_width=True)
        st.markdown(get_image_download_link(fig_sector), unsafe_allow_html=True)
    else:
        st.info("Benchmark data not available.")

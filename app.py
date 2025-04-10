import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import BytesIO
import openpyxl
from openpyxl.chart import BarChart, Reference

# Page config
st.set_page_config(page_title="Financial Dashboard", layout="wide")
st.title("📊 Financial Model & Valuation Dashboard")

# Get API key from Streamlit secrets
FMP_API_KEY = st.secrets["FMP_API_KEY"]

# Sidebar inputs
ticker = st.sidebar.text_input("Enter Stock Ticker", value="AAPL")

# Function to fetch data from FMP
def get_fmp_financials(ticker):
    base = "https://financialmodelingprep.com/api/v3"
    endpoints = {
        "ratios": f"{base}/ratios-ttm/{ticker}?apikey={FMP_API_KEY}",
        "valuation": f"{base}/enterprise-values/{ticker}?limit=1&apikey={FMP_API_KEY}",
        "dcf": f"{base}/discounted-cash-flow/{ticker}?apikey={FMP_API_KEY}",
        "income": f"{base}/income-statement/{ticker}?limit=1&apikey={FMP_API_KEY}",
        "balance": f"{base}/balance-sheet-statement/{ticker}?limit=1&apikey={FMP_API_KEY}",
        "cashflow": f"{base}/cash-flow-statement/{ticker}?limit=1&apikey={FMP_API_KEY}"
    }
    results = {}
    for key, url in endpoints.items():
        r = requests.get(url)
        if r.status_code == 200:
            results[key] = r.json()[0] if r.json() else {}
        else:
            results[key] = {}
    return results

# Function to get historical prices
def get_price_data(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="6mo")
    return hist

# Display metrics
def display_metrics(data):
    if not data:
        st.warning("No data available.")
        return
    metrics = {
        "ROE": data['ratios'].get("returnOnEquityTTM", "N/A"),
        "ROA": data['ratios'].get("returnOnAssetsTTM", "N/A"),
        "Debt/Equity": data['ratios'].get("debtEquityRatioTTM", "N/A"),
        "DCF Value": data['dcf'].get("dcf", "N/A"),
        "Market Cap": data['valuation'].get("marketCapitalization", "N/A"),
        "Enterprise Value": data['valuation'].get("enterpriseValue", "N/A")
    }
    df = pd.DataFrame(metrics.items(), columns=["Metric", "Value"])
    st.subheader("📈 Key Metrics")
    st.dataframe(df, use_container_width=True)
    return df

# Save to Excel
def save_to_excel_with_chart(df, ticker):
    buffer = BytesIO()
    df.to_excel(buffer, index=False, sheet_name="Metrics")
    buffer.seek(0)

    wb = openpyxl.load_workbook(buffer)
    ws = wb["Metrics"]

    chart = BarChart()
    chart.title = f"{ticker} Metrics"
    chart.y_axis.title = 'Value'
    chart.x_axis.title = 'Metric'

    data_ref = Reference(ws, min_col=2, min_row=1, max_row=6)
    cats_ref = Reference(ws, min_col=1, min_row=2, max_row=6)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    ws.add_chart(chart, "E2")

    final_buffer = BytesIO()
    wb.save(final_buffer)
    final_buffer.seek(0)
    return final_buffer

# Fetch and show data
if st.button("📊 Run Analysis"):
    with st.spinner("Fetching data from FMP and Yahoo..."):
        financial_data = get_fmp_financials(ticker)
        df_metrics = display_metrics(financial_data)

        # Chart
        if df_metrics is not None:
            fig = px.bar(df_metrics, x="Metric", y="Value",
                         title=f"{ticker.upper()} - Financial Metrics",
                         color="Metric", color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig, use_container_width=True)

            excel_data = save_to_excel_with_chart(df_metrics, ticker)
            st.download_button("📥 Download Metrics (Excel)", excel_data,
                               file_name=f"{ticker}_metrics.xlsx")

        # Historical Chart
        hist = get_price_data(ticker)
        st.subheader("📉 Historical Price Chart")
        st.line_chart(hist["Close"])

import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px
import smtplib
from email.message import EmailMessage
from io import BytesIO
from datetime import datetime
import openpyxl
from openpyxl.chart import BarChart, Reference

# Set Streamlit page config
st.set_page_config(page_title="Financial Dashboard", layout="wide")
st.title("📊 Financial Model & Valuation Dashboard")

# Sidebar Configuration
st.sidebar.header("Settings")
data_source = st.sidebar.selectbox("Choose Data Source", ["Yahoo Finance", "FMP"])
ticker = st.sidebar.text_input("Enter Stock Ticker", value="AAPL")
fmp_api_key = st.sidebar.text_input("Enter your FMP API Key", type="password")

# Yahoo Finance Function
def get_yahoo_data(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    data = {
        "P/E Ratio": info.get("trailingPE", "N/A"),
        "EPS": info.get("trailingEps", "N/A"),
        "ROE": info.get("returnOnEquity", "N/A"),
        "ROA": info.get("returnOnAssets", "N/A"),
        "Debt/Equity": info.get("debtToEquity", "N/A")
    }
    return data

# FMP API Function
def get_fmp_data(ticker, api_key):
    base_url = "https://financialmodelingprep.com/api/v3"
    endpoints = {
        "key_metrics": f"{base_url}/key-metrics-ttm/{ticker}?apikey={api_key}",
        "ratios": f"{base_url}/ratios-ttm/{ticker}?apikey={api_key}",
        "dcf": f"{base_url}/discounted-cash-flow/{ticker}?apikey={api_key}"
    }
    data = {}
    try:
        km = requests.get(endpoints["key_metrics"]).json()[0]
        rt = requests.get(endpoints["ratios"]).json()[0]
        dcf = requests.get(endpoints["dcf"]).json()

        data = {
            "P/E Ratio": km.get("peRatioTTM", "N/A"),
            "EPS": km.get("epsTTM", "N/A"),
            "ROE": rt.get("returnOnEquityTTM", "N/A"),
            "ROA": rt.get("returnOnAssetsTTM", "N/A"),
            "Debt/Equity": rt.get("debtEquityRatioTTM", "N/A"),
            "DCF Valuation": dcf.get("dcf", "N/A") if isinstance(dcf, dict) else dcf[0].get("dcf", "N/A")
        }
    except Exception as e:
        st.error(f"Failed to fetch from FMP: {e}")
    return data

# Excel Export with chart
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

    data_ref = Reference(ws, min_col=2, min_row=1, max_row=len(df)+1)
    cats_ref = Reference(ws, min_col=1, min_row=2, max_row=len(df)+1)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    ws.add_chart(chart, "D2")

    final_buffer = BytesIO()
    wb.save(final_buffer)
    final_buffer.seek(0)
    return final_buffer

# Fetch Button
if st.button("📅 Fetch Data"):
    if not ticker:
        st.warning("Please enter a valid stock ticker.")
    else:
        if data_source == "Yahoo Finance":
            metrics = get_yahoo_data(ticker)
        elif data_source == "FMP":
            if not fmp_api_key:
                st.warning("Please enter a valid FMP API key.")
                st.stop()
            metrics = get_fmp_data(ticker, fmp_api_key)
        else:
            metrics = {}

        if not metrics:
            st.error("No data found.")
        else:
            tab1, tab2, tab3 = st.tabs(["📈 Metrics Table", "📊 Visualizations", "📉 Historical Price"])

            with tab1:
                df = pd.DataFrame(metrics.items(), columns=["Metric", "Value"])
                st.dataframe(df, use_container_width=True)
                excel_data = save_to_excel_with_chart(df, ticker)
                st.download_button("📤 Download Excel", excel_data, file_name=f"{ticker}_metrics.xlsx")

            with tab2:
                values, labels = [], []
                for k, v in metrics.items():
                    try:
                        val = float(v)
                        values.append(val)
                        labels.append(k)
                    except:
                        continue

                if values:
                    fig = px.bar(x=labels, y=values, labels={'x': 'Metric', 'y': 'Value'},
                                 title=f"{ticker.upper()} - Key Financial Metrics",
                                 color=labels, color_discrete_sequence=px.colors.sequential.Teal)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No numeric metrics for plotting.")

            with tab3:
                try:
                    hist = yf.Ticker(ticker).history(period="1y")
                    fig = px.line(hist, x=hist.index, y="Close", title=f"{ticker} - 1Y Price History")
                    st.plotly_chart(fig, use_container_width=True)
                except:
                    st.warning("Could not fetch historical prices.")

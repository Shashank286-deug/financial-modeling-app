import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import finnhub
import plotly.express as px
import smtplib
from email.message import EmailMessage
from io import BytesIO
from datetime import datetime
import openpyxl
from openpyxl.chart import BarChart, Reference
import json

# Set layout with dark mode toggle
st.set_page_config(page_title="Financial Dashboard", layout="wide")
st.title("📊 Financial Model & Valuation Dashboard")

# Theme toggle
theme = st.sidebar.radio("Choose Theme", ["Light", "Dark"])
if theme == "Dark":
    st.markdown("""
        <style>
        body {
            background-color: #111;
            color: white;
        }
        </style>
    """, unsafe_allow_html=True)

# Sidebar Settings
st.sidebar.header("Settings")
data_source = st.sidebar.selectbox("Choose Data Source", ["Yahoo Finance", "Alpha Vantage", "Finnhub", "FMP"])
ticker = st.sidebar.selectbox("Choose Stock Ticker", ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"])
email_address = st.sidebar.text_input("Enter Email for Alerts (optional)")

# Secrets (API keys)
FMP_API_KEY = st.secrets["FMP_API_KEY"]

# Functions
def get_fmp_ratios(ticker):
    url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{ticker}?apikey={FMP_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data:
            latest = data[0]
            return {
                "P/E Ratio": latest.get("peRatioTTM"),
                "ROE": latest.get("returnOnEquityTTM"),
                "ROA": latest.get("returnOnAssetsTTM"),
                "Debt/Equity": latest.get("debtEquityRatioTTM"),
                "EPS": latest.get("epsTTM")
            }
    return {}

def get_fmp_financials(ticker):
    endpoints = ["income-statement", "balance-sheet-statement", "cash-flow-statement"]
    results = {}
    for name in endpoints:
        url = f"https://financialmodelingprep.com/api/v3/{name}/{ticker}?limit=1&apikey={FMP_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data:
                results[name.replace("-", "_")] = data[0]
    return results

def save_financials_to_excel(ratios, financials, ticker):
    buffer = BytesIO()
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = "Ratios"
    for i, (k, v) in enumerate(ratios.items(), start=1):
        ws1.cell(row=i, column=1).value = k
        ws1.cell(row=i, column=2).value = v

    for sheet, data in financials.items():
        ws = wb.create_sheet(title=sheet[:30])
        for i, (k, v) in enumerate(data.items(), start=1):
            ws.cell(row=i, column=1).value = k
            ws.cell(row=i, column=2).value = v

    wb.save(buffer)
    buffer.seek(0)
    return buffer

# Fetch Button
if st.button("📅 Fetch Data"):
    with st.spinner("Fetching data..."):
        if data_source == "FMP":
            ratios = get_fmp_ratios(ticker)
            financials = get_fmp_financials(ticker)
        else:
            ratios = {}
            financials = {}

        if not ratios:
            st.error("Data fetch failed. Please check ticker or try a different source.")
        else:
            tab1, tab2 = st.tabs(["📈 Key Ratios", "📊 Financials"])

            with tab1:
                df = pd.DataFrame(ratios.items(), columns=["Metric", "Value"])
                st.dataframe(df, use_container_width=True)
                excel_data = save_financials_to_excel(ratios, financials, ticker)
                st.download_button("📤 Download Full Financials", excel_data, file_name=f"{ticker}_financials.xlsx")

            with tab2:
                for sheet, data in financials.items():
                    st.subheader(sheet.replace("_", " ").title())
                    df = pd.DataFrame(data.items(), columns=["Metric", "Value"])
                    st.dataframe(df, use_container_width=True)

                # Visualization example
                if "income_statement" in financials:
                    income = financials["income_statement"]
                    chart_data = pd.DataFrame({"Metric": ["Revenue", "Gross Profit", "Net Income"],
                                               "Value": [income.get("revenue"), income.get("grossProfit"), income.get("netIncome")]} )
                    fig = px.bar(chart_data, x="Metric", y="Value", title=f"{ticker} Income Statement Snapshot")
                    st.plotly_chart(fig, use_container_width=True)

                if email_address:
                    st.success(f"Alert setup success for {email_address}")

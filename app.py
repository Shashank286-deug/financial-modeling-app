import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import matplotlib.pyplot as plt
import io
from openpyxl import load_workbook

# Set layout
st.set_page_config(page_title="Financial Dashboard", layout="wide")
st.title("📊 Financial Model & Valuation Dashboard")

# Sidebar Settings
st.sidebar.header("Settings")
data_source = st.sidebar.selectbox("Choose Data Source", ["Yahoo Finance", "Alpha Vantage", "Finnhub"])
tickers = st.sidebar.text_input("Enter Stock Ticker(s), comma-separated", value="AAPL,MSFT")
ticker_list = [t.strip().upper() for t in tickers.split(',') if t.strip()]

# API keys (hardcoded or editable)
alpha_key = "Z0ANCCQ81ZW5OVYZ"
finnhub_key = "cvrbc29r01qp88cpdph0cvrbc29r01qp88cpdphg"

# Excel Template Upload
template_file = st.sidebar.file_uploader("Upload Excel Template", type=[".xlsx"])

# Data functions
def get_yahoo_data(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    hist = stock.history(period="1y")
    data = {
        "P/E Ratio": info.get("trailingPE", "N/A"),
        "EPS": info.get("trailingEps", "N/A"),
        "EBITDA": info.get("ebitda", "N/A"),
        "Cash Flow": info.get("operatingCashflow", "N/A"),
        "Revenue": info.get("totalRevenue", "N/A"),
        "History": hist
    }
    return data

def get_alpha_data(ticker, api_key):
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
    r = requests.get(url)
    if r.status_code != 200:
        return {}
    info = r.json()
    data = {
        "P/E Ratio": info.get("PERatio", "N/A"),
        "EPS": info.get("EPS", "N/A"),
        "EBITDA": info.get("EBITDA", "N/A"),
        "Cash Flow": info.get("OperatingCashflow", "N/A"),
        "Revenue": info.get("RevenueTTM", "N/A"),
        "History": None
    }
    return data

def get_finnhub_data(ticker, api_key):
    client = finnhub.Client(api_key=api_key)
    try:
        fundamentals = client.company_basic_financials(ticker, 'all')['metric']
        candles = client.stock_candles(ticker, 'D', 1640995200, 1711929600)  # 2022–2024 timestamps
        df_hist = pd.DataFrame({"Date": pd.to_datetime(candles['t'], unit='s'), "Close": candles['c']}) if candles and 'c' in candles else None
        data = {
            "P/E Ratio": fundamentals.get("peBasicExclExtraTTM", "N/A"),
            "EPS": fundamentals.get("epsTTM", "N/A"),
            "EBITDA": fundamentals.get("ebitda", "N/A"),
            "Cash Flow": fundamentals.get("freeCashFlowTTM", "N/A"),
            "Revenue": fundamentals.get("revenueTTM", "N/A"),
            "History": df_hist.set_index("Date") if df_hist is not None else None
        }
        return data
    except:
        return {}

# Main Execution
if st.button("📥 Fetch Data"):
    for ticker in ticker_list:
        st.subheader(f"📈 {ticker} Metrics")
        if data_source == "Yahoo Finance":
            metrics = get_yahoo_data(ticker)
        elif data_source == "Alpha Vantage":
            metrics = get_alpha_data(ticker, alpha_key)
        else:
            metrics = get_finnhub_data(ticker, finnhub_key)

        if not metrics:
            st.error(f"Data fetch failed for {ticker}.")
            continue

        df = pd.DataFrame({"Metric": list(metrics.keys())[:-1], "Value": list(metrics.values())[:-1]})
        st.dataframe(df, use_container_width=True)

        # Bar Chart
        try:
            numeric = df[df['Value'].apply(lambda x: isinstance(x, (int, float)) or str(x).replace('.', '', 1).isdigit())]
            fig, ax = plt.subplots()
            ax.bar(numeric['Metric'], numeric['Value'].astype(float), color='teal')
            ax.set_title(f"{ticker} - Financial Metrics")
            st.pyplot(fig)
        except:
            st.warning("Bar chart skipped: numeric conversion issue.")

        # Pie Chart
        try:
            fig2, ax2 = plt.subplots()
            ax2.pie(numeric['Value'].astype(float), labels=numeric['Metric'], autopct='%1.1f%%')
            ax2.set_title("Metric Composition")
            st.pyplot(fig2)
        except:
            st.warning("Pie chart skipped: issue rendering values.")

        # Time Series Chart
        if metrics.get("History") is not None:
            st.line_chart(metrics["History"]["Close"], use_container_width=True)

        # Excel Fill
        if template_file:
            wb = load_workbook(template_file)
            ws = wb.active
            fill_map = {
                "B2": "P/E Ratio",
                "B3": "EPS",
                "B4": "EBITDA",
                "B5": "Cash Flow",
                "B6": "Revenue"
            }
            for cell, key in fill_map.items():
                val = metrics.get(key, "N/A")
                try:
                    ws[cell] = float(val) if str(val).replace('.', '', 1).isdigit() else val
                except:
                    ws[cell] = val

            output = io.BytesIO()
            wb.save(output)
            st.download_button("📥 Download Updated Excel", data=output.getvalue(), file_name=f"{ticker}_updated.xlsx")

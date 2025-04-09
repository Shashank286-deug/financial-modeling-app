import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import matplotlib.pyplot as plt
import finnhub

# Set layout
st.set_page_config(page_title="Financial Dashboard", layout="wide")
st.title("📊 Financial Model & Valuation Dashboard")

# Sidebar Settings
st.sidebar.header("Settings")
data_source = st.sidebar.selectbox("Choose Data Source", ["Yahoo Finance", "Alpha Vantage", "Finnhub"])
ticker = st.sidebar.text_input("Enter Stock Ticker", value="AAPL")

# API keys
alpha_key = st.sidebar.text_input("Alpha Vantage API Key", value="Z0ANCCQ81ZW5OVYZ") if data_source == "Alpha Vantage" else None
finnhub_key = st.sidebar.text_input("Finnhub API Key", value="cvrbc29r01qp88cpdph0cvrbc29r01qp88cpdphg", type="password") if data_source == "Finnhub" else None

# Functions
def get_yahoo_data(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    data = {
        "P/E Ratio": info.get("trailingPE", "N/A"),
        "EPS": info.get("trailingEps", "N/A"),
        "EBITDA": info.get("ebitda", "N/A"),
        "Cash Flow": info.get("operatingCashflow", "N/A"),
        "Revenue": info.get("totalRevenue", "N/A")
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
        "Revenue": info.get("RevenueTTM", "N/A")
    }
    return data

def get_finnhub_data(ticker, api_key):
    if not api_key:
        return {}
    client = finnhub.Client(api_key=api_key)
    try:
        quote = client.quote(ticker)
        profile = client.company_profile2(symbol=ticker)
        fundamentals = client.company_basic_financials(ticker, 'all')['metric']

        data = {
            "P/E Ratio": fundamentals.get("peBasicExclExtraTTM", "N/A"),
            "EPS": fundamentals.get("epsTTM", "N/A"),
            "EBITDA": fundamentals.get("ebitda", "N/A"),
            "Cash Flow": fundamentals.get("freeCashFlowTTM", "N/A"),
            "Revenue": fundamentals.get("revenueTTM", "N/A")
        }
        return data
    except:
        return {}

# Main Button
if st.button("📥 Fetch Data"):
    with st.spinner("Fetching data..."):
        if data_source == "Yahoo Finance":
            metrics = get_yahoo_data(ticker)
        elif data_source == "Alpha Vantage":
            metrics = get_alpha_data(ticker, alpha_key)
        elif data_source == "Finnhub":
            metrics = get_finnhub_data(ticker, finnhub_key)
        else:
            metrics = {}

        if not metrics:
            st.error("Data fetch failed. Please check ticker or API keys.")
        else:
            st.subheader("📈 Key Metrics")
            df = pd.DataFrame(metrics.items(), columns=["Metric", "Value"])
            st.dataframe(df, use_container_width=True)

            try:
                fig, ax = plt.subplots()
                values = [float(v) for v in metrics.values() if isinstance(v, (int, float)) or (str(v).replace('.', '', 1).isdigit())]
                labels = [k for k, v in metrics.items() if isinstance(v, (int, float)) or (str(v).replace('.', '', 1).isdigit())]
                ax.bar(labels, values, color='teal')
                ax.set_title(f"{ticker.upper()} - Key Financial Metrics")
                ax.set_ylabel("USD")
                ax.set_xticklabels(labels, rotation=45)
                st.pyplot(fig)
            except:
                st.warning("Some values may not be numeric for visualization.")

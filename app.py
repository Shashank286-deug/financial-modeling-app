import streamlit as st
import yfinance as yf
import requests
import finnhub
import pandas as pd
import matplotlib.pyplot as plt


# Set layout
st.set_page_config(page_title="Financial Dashboard", layout="wide")
st.title("📊 Financial Model & Valuation Dashboard")

# Sidebar Settings
st.sidebar.header("Settings")
data_source = st.sidebar.selectbox("Choose Data Source", ["Yahoo Finance", "Alpha Vantage", "Finnhub"])
ticker = st.sidebar.text_input("Enter Stock Ticker", value="AAPL")

# Hardcoded API keys
ALPHA_VANTAGE_API_KEY = "Q8LU981EWC83K7VI"
FINNHUB_API_KEY = "cvrbc29r01qp88cpdph0cvrbc29r01qp88cpdphg"

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

def get_alpha_data(ticker):
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
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

def get_finnhub_data(ticker):
    client = finnhub.Client(api_key=FINNHUB_API_KEY)
    try:
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

# Main Logic
if st.button("📅 Fetch Data"):
    with st.spinner("Fetching data..."):
        if data_source == "Yahoo Finance":
            metrics = get_yahoo_data(ticker)
        elif data_source == "Alpha Vantage":
            metrics = get_alpha_data(ticker)
        elif data_source == "Finnhub":
            metrics = get_finnhub_data(ticker)
        else:
            metrics = {}

        if not metrics:
            st.error("Data fetch failed. Please check ticker or try a different source.")
        else:
            st.subheader("📈 Key Metrics")
            df = pd.DataFrame(metrics.items(), columns=["Metric", "Value"])
            st.dataframe(df, use_container_width=True)

            # Visual
            try:
                values = []
                labels = []
                for k, v in metrics.items():
                    try:
                        val = float(v)
                        values.append(val)
                        labels.append(k)
                    except:
                        continue

                if values:
                    fig, ax = plt.subplots()
                    ax.bar(labels, values, color='teal')
                    ax.set_title(f"{ticker.upper()} - Key Financial Metrics")
                    ax.set_ylabel("USD")
                    ax.set_xticks(range(len(labels)))
                    ax.set_xticklabels(labels, rotation=45)
                    st.pyplot(fig)
                else:
                    st.warning("No numeric values found for visualization.")
            except:
                st.warning("Visualization failed. Please check values.")

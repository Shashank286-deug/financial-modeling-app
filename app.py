import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import matplotlib.pyplot as plt

# Set Streamlit layout
st.set_page_config(page_title="Financial Model Dashboard", layout="wide")

# Title
st.title("📊 Financial Model & Valuation Dashboard")

# Sidebar for user input
st.sidebar.header("Settings")
data_source = st.sidebar.radio("Choose Data Source", ["Yahoo Finance", "Alpha Vantage"])
ticker = st.sidebar.text_input("Enter Stock Ticker", value="AAPL")
alpha_key = st.sidebar.text_input("Alpha Vantage API Key", value="Q8LU981EWC83K7VI")

# Define Yahoo Finance function
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

# Define Alpha Vantage function
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

# Fetch and display data
if st.button("📥 Fetch Data"):
    with st.spinner("Fetching data..."):
        if data_source == "Yahoo Finance":
            metrics = get_yahoo_data(ticker)
        else:
            metrics = get_alpha_data(ticker, alpha_key)

        if not metrics:
            st.error("Data fetch failed. Please check the ticker or API key.")
        else:
            st.subheader("📈 Key Valuation Metrics")
            df_metrics = pd.DataFrame(metrics.items(), columns=["Metric", "Value"])
            st.dataframe(df_metrics, use_container_width=True)

            # Visual
            fig, ax = plt.subplots()
            try:
                vals = [float(v) for v in metrics.values() if isinstance(v, (int, float, str)) and str(v).replace('.', '', 1).isdigit()]
                labels = [k for k, v in metrics.items() if isinstance(v, (int, float, str)) and str(v).replace('.', '', 1).isdigit()]
                ax.bar(labels, vals, color='skyblue')
                ax.set_title(f"{ticker.upper()} Metrics Visual")
                ax.set_ylabel("USD")
                ax.set_xticklabels(labels, rotation=45)
                st.pyplot(fig)
            except:
                st.info("Some metrics are not numeric and can't be visualized.")


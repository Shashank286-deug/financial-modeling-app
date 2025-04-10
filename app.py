import streamlit as st
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime

# App config
st.set_page_config(page_title="Financial Modeling App", layout="wide")

# Sidebar Inputs
st.sidebar.title("Settings")
data_source = st.sidebar.selectbox("Choose Data Source", ["Yahoo Finance", "FMP"])
ticker = st.sidebar.text_input("Enter Stock Ticker", "AAPL")
email = st.sidebar.text_input("Enter Email for Alerts (optional)")
theme = st.sidebar.radio("Choose Theme", ["Light", "Dark"])

st.markdown(f"<style>body {{ background-color: {'#0e1117' if theme == 'Dark' else '#FFFFFF'}; }}</style>", unsafe_allow_html=True)

# Fetch button
if st.button("🔄 Fetch Data"):
    if data_source == "Yahoo Finance":
        stock = yf.Ticker(ticker)
        info = stock.info
        if info:
            df = pd.DataFrame.from_dict(info, orient='index', columns=['Value']).reset_index()
        else:
            st.error("Failed to fetch data from Yahoo Finance.")
            df = pd.DataFrame()

    elif data_source == "FMP":
        fmp_api_key = "uPJt4YPx3t5TRmcCpS7emobdeRLAngRG"  # You should store this securely in .env or secrets
        url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={fmp_api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame.from_dict(data[0], orient='index', columns=['Value']).reset_index()
            else:
                st.error("No data found for this ticker from FMP.")
                df = pd.DataFrame()
        else:
            st.error("Failed to fetch data from FMP API.")
            df = pd.DataFrame()

    # Show Metrics
    st.subheader("📉 Key Metrics")

    if not df.empty and "Value" in df.columns:
        styled_df = df.style.format({"Value": "{:.2f}"}).highlight_null(null_color='red').set_properties(**{'text-align': 'center'})
        st.dataframe(styled_df)
    else:
        st.warning("No data available or 'Value' column missing. Please try a different ticker or source.")

    # Optional Debug
    # st.write("Raw DF:")
    # st.write(df)

# Tabs for Visualization (Placeholder)
tabs = st.tabs(["📊 Metrics Table", "📈 Visualizations"])
with tabs[0]:
    st.write("Table view will go here")
with tabs[1]:
    st.write("Visual charts will go here")

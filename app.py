import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime
import openpyxl
from openpyxl.chart import BarChart, Reference

# Set Streamlit page config
st.set_page_config(page_title="Financial Dashboard", layout="wide")
st.title("📊 Financial Model & Valuation Dashboard")

# Sidebar options
st.sidebar.header("Settings")
data_source = st.sidebar.selectbox("Choose Data Source", ["FMP"])
ticker = st.sidebar.text_input("Enter Stock Ticker", value="AAPL")

# Replace with your FMP API key
FMP_API_KEY = "uPJt4YPx3t5TRmcCpS7emobdeRLAngRG"

def get_fmp_data(ticker):
    url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={FMP_API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        return {}
    data = response.json()
    if not data:
        return {}
    item = data[0]
    return {
        "Company Name": item.get("companyName", "N/A"),
        "P/E Ratio": item.get("pe", "N/A"),
        "EPS": item.get("eps", "N/A"),
        "Market Cap": item.get("mktCap", "N/A"),
        "Industry": item.get("industry", "N/A"),
        "Exchange": item.get("exchange", "N/A")
    }

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

    ws.add_chart(chart, "E2")

    final_buffer = BytesIO()
    wb.save(final_buffer)
    final_buffer.seek(0)
    return final_buffer

if st.button("🔍 Fetch Data"):
    if data_source == "FMP":
        data = get_fmp_data(ticker)

        if not data:
            st.error("No data found. Please check the ticker symbol.")
        else:
            st.subheader("📋 Key Metrics")
            df = pd.DataFrame(data.items(), columns=["Metric", "Value"])

            try:
                styled_df = df.style.format({"Value": "{:.2f}"}).highlight_null(null_color='red').set_properties(**{'text-align': 'center'})
                st.dataframe(styled_df, use_container_width=True)
            except:
                st.dataframe(df, use_container_width=True)

            # Plotly Visualization
            try:
                numeric_df = df.copy()
                numeric_df["Value"] = pd.to_numeric(numeric_df["Value"], errors='coerce')
                numeric_df.dropna(inplace=True)

                fig = px.bar(numeric_df, x="Metric", y="Value", color="Metric", title=f"{ticker.upper()} - Key Metrics")
                st.plotly_chart(fig, use_container_width=True)
            except:
                st.warning("Could not generate visualization.")

            # Excel Export
            excel_data = save_to_excel_with_chart(df, ticker)
            st.download_button("📥 Download Excel", data=excel_data, file_name=f"{ticker}_metrics.xlsx")

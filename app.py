import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from io import BytesIO
from datetime import datetime
import openpyxl
from openpyxl.chart import BarChart, Reference

# Streamlit Page Config
st.set_page_config(page_title="📊 Financial Dashboard", layout="wide")
st.title("📊 Financial Model & Valuation Dashboard")

# Sidebar Inputs
api_key = st.sidebar.text_input("Enter your FMP API Key", type="password")
ticker = st.sidebar.text_input("Enter Stock Ticker", value="AAPL")

# Helper Functions
def fetch_fmp_data(endpoint, ticker, api_key):
    url = f"https://financialmodelingprep.com/api/v3/{endpoint}/{ticker}?apikey={api_key}"
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    return None

def parse_key_metrics(data):
    metrics = {
        "P/E Ratio": data.get("peRatio", "N/A"),
        "EPS": data.get("eps", "N/A"),
        "EBITDA": data.get("ebitda", "N/A"),
        "Revenue": data.get("revenue", "N/A"),
        "Cash Flow": data.get("freeCashFlow", "N/A"),
        "ROE": data.get("roe", "N/A"),
        "ROA": data.get("roa", "N/A"),
        "Debt/Equity": data.get("debtEquityRatio", "N/A")
    }
    return metrics

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

# Main
if st.button("📥 Fetch & Visualize Data"):
    if not api_key:
        st.warning("Please enter a valid FMP API Key.")
    else:
        with st.spinner("Fetching data from FMP..."):
            profile = fetch_fmp_data("profile", ticker, api_key)
            ratios = fetch_fmp_data("ratios-ttm", ticker, api_key)
            income = fetch_fmp_data("income-statement", ticker, api_key)
            balance = fetch_fmp_data("balance-sheet-statement", ticker, api_key)
            cashflow = fetch_fmp_data("cash-flow-statement", ticker, api_key)

            if profile and len(profile) > 0 and ratios and len(ratios) > 0:
                data = profile[0]
                metrics = parse_key_metrics(ratios[0])

                tab1, tab2, tab3 = st.tabs(["📈 Key Metrics", "📊 Visualizations", "📁 Financial Statements"])

                with tab1:
                    df = pd.DataFrame(metrics.items(), columns=["Metric", "Value"])
                    st.dataframe(df.style.set_precision(2), use_container_width=True)

                    excel_data = save_to_excel_with_chart(df, ticker)
                    st.download_button("📤 Download Metrics Excel", excel_data, file_name=f"{ticker}_metrics.xlsx")

                with tab2:
                    try:
                        numeric_data = [(k, float(v)) for k, v in metrics.items() if v != "N/A"]
                        if numeric_data:
                            labels, values = zip(*numeric_data)
                            fig = px.bar(x=labels, y=values, title=f"{ticker} - Key Financial Metrics")
                            st.plotly_chart(fig, use_container_width=True)
                    except:
                        st.warning("Unable to create visualization.")

                with tab3:
                    st.subheader("📜 Income Statement")
                    st.dataframe(pd.DataFrame(income[:1]))
                    st.subheader("🏦 Balance Sheet")
                    st.dataframe(pd.DataFrame(balance[:1]))
                    st.subheader("💸 Cash Flow Statement")
                    st.dataframe(pd.DataFrame(cashflow[:1]))
            else:
                st.error("Failed to fetch data. Check ticker symbol and API key.")

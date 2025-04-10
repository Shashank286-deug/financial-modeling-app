import streamlit as st

import requests
import pandas as pd

import matplotlib.pyplot as plt


import smtplib
from email.message import EmailMessage
from io import BytesIO
from datetime import datetime

from openpyxl.chart import BarChart, Reference
import time

# --- CONFIG ---
FMP_API_KEY = "demo"  # Replace with your actual key
ALPHA_VANTAGE_API_KEY = "Q8LU981EWC83K7VI"
FINNHUB_API_KEY = "cvrbc29r01qp88cpdph0cvrbc29r01qp88cpdphg"

# --- STREAMLIT SETUP ---
st.set_page_config(page_title="Financial Dashboard", layout="wide")
st.title("📊 Financial Model & Valuation Dashboard")

# --- SIDEBAR ---
st.sidebar.header("Settings")
theme = st.sidebar.radio("Choose Theme", ["Light", "Dark"])
data_source = st.sidebar.selectbox("Choose Data Source", ["Yahoo Finance", "Alpha Vantage", "Finnhub", "FMP"])
ticker = st.sidebar.text_input("Enter Stock Ticker", value="AAPL")
email_address = st.sidebar.text_input("Enter Email for Alerts (optional)")

if theme == "Dark":
    st.markdown("""
        <style>
        body {
            background-color: #111;
            color: white;
        }
        </style>
    """, unsafe_allow_html=True)

# --- DATA FETCH FUNCTIONS ---
def get_yahoo_data(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    return {
        "P/E Ratio": info.get("trailingPE", "N/A"),
        "EPS": info.get("trailingEps", "N/A"),
        "EBITDA": info.get("ebitda", "N/A"),
        "Cash Flow": info.get("operatingCashflow", "N/A"),
        "Revenue": info.get("totalRevenue", "N/A")
    }

def get_alpha_data(ticker):
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
    r = requests.get(url)
    info = r.json()
    return {
        "P/E Ratio": info.get("PERatio", "N/A"),
        "EPS": info.get("EPS", "N/A"),
        "EBITDA": info.get("EBITDA", "N/A"),
        "Cash Flow": info.get("OperatingCashflow", "N/A"),
        "Revenue": info.get("RevenueTTM", "N/A")
    } if r.status_code == 200 else {}

def get_finnhub_data(ticker):
    client = finnhub.Client(api_key=FINNHUB_API_KEY)
    try:
        fundamentals = client.company_basic_financials(ticker, 'all')['metric']
        return {
            "P/E Ratio": fundamentals.get("peBasicExclExtraTTM", "N/A"),
            "EPS": fundamentals.get("epsTTM", "N/A"),
            "EBITDA": fundamentals.get("ebitda", "N/A"),
            "Cash Flow": fundamentals.get("freeCashFlowTTM", "N/A"),
            "Revenue": fundamentals.get("revenueTTM", "N/A")
        }
    except:
        return {}

def get_fmp_data(ticker, api_key=FMP_API_KEY):
    url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={api_key}"
    response = requests.get(url)
    if response.status_code != 200 or not response.json():
        return {}
    profile = response.json()[0]
    return {
        "P/E Ratio": profile.get("pe"),
        "EPS": profile.get("eps"),
        "EBITDA": profile.get("ebitda"),
        "Cash Flow": profile.get("freeCashFlow"),
        "Revenue": profile.get("revenue")
    }

# --- EMAIL ALERT ---
def send_email_alert(receiver, subject, body):
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = "financial-dashboard@example.com"
        msg['To'] = receiver
        msg.set_content(body)
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            # server.login("you@example.com", "password")
            # server.send_message(msg)
            pass
        return True
    except:
        return False

# --- EXCEL EXPORT ---
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
    ws.add_chart(chart, "D2")
    final_buffer = BytesIO()
    wb.save(final_buffer)
    final_buffer.seek(0)
    return final_buffer

# --- FETCH DATA ---
if st.button("📅 Fetch Data"):
    with st.spinner("Fetching data..."):
        if data_source == "Yahoo Finance":
            metrics = get_yahoo_data(ticker)
        elif data_source == "Alpha Vantage":
            metrics = get_alpha_data(ticker)
        elif data_source == "Finnhub":
            metrics = get_finnhub_data(ticker)
        elif data_source == "FMP":
            metrics = get_fmp_data(ticker)
        else:
            metrics = {}

        if not metrics:
            st.error("Data fetch failed. Please check ticker or try a different source.")
        else:
            tab1, tab2 = st.tabs(["📈 Metrics Table", "📊 Visualizations"])

            with tab1:
                st.subheader("📈 Key Metrics")
                df = pd.DataFrame(metrics.items(), columns=["Metric", "Value"])
                styled_df = df.style.format({"Value": "{:.2f}"}).highlight_null(null_color='red').set_properties(**{'background-color': '#f4f4f4', 'border': '1px solid #ddd'})
                st.dataframe(styled_df, use_container_width=True)

                excel_data = save_to_excel_with_chart(df, ticker)
                st.download_button("📤 Download as Excel", excel_data, file_name=f"{ticker}_metrics.xlsx")

                history_df = pd.DataFrame([[datetime.now().isoformat(), ticker, data_source]], columns=["Timestamp", "Ticker", "Source"])
                try:
                    history_df.to_csv("ticker_history.csv", mode='a', index=False, header=not pd.io.common.file_exists("ticker_history.csv"))
                except:
                    pass

                if email_address:
                    success = send_email_alert(email_address, f"Metrics for {ticker}", df.to_string(index=False))
                    if success:
                        st.success(f"Email alert sent to {email_address}!")
                    else:
                        st.warning("Failed to send email. Check configuration.")

            with tab2:
                try:
                    values, labels = [], []
                    for k, v in metrics.items():
                        try:
                            values.append(float(v))
                            labels.append(k)
                        except:
                            continue
                    if values:
                        fig = px.bar(x=labels, y=values, labels={'x': 'Metric', 'y': 'Value'},
                                     title=f"{ticker.upper()} - Key Financial Metrics",
                                     color=labels, color_discrete_sequence=px.colors.sequential.Teal)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("No numeric values found for visualization.")
                except:
                    st.warning("Visualization failed. Please check values.")

import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import matplotlib.pyplot as plt
import io
from openpyxl import load_workbook, Workbook
from openpyxl.chart import LineChart, Reference
import os
import json
import datetime
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Set layout
st.set_page_config(page_title="Financial Dashboard", layout="wide")
st.title("📊 Financial Model & Valuation Dashboard")

# Sidebar Settings
st.sidebar.header("Settings")
data_source = st.sidebar.selectbox("Choose Data Source", ["Yahoo Finance", "Alpha Vantage", "Finnhub"])
ticker_input = st.sidebar.text_input("Enter Stock Ticker(s), comma-separated", value="AAPL,MSFT")
search_query = st.sidebar.text_input("Search historical tickers")

# Filter history
filtered_history = []
if search_query:
    with open("ticker_history.json", 'r') as f:
        all_tickers = json.load(f)
    filtered_history = [t for t in all_tickers if search_query.upper() in t.upper()]
    st.sidebar.write("Matches:", filtered_history)

# Schedule auto-refresh (simulate periodic fetch)
refresh = st.sidebar.checkbox("⏰ Enable Auto Refresh", value=False)
interval = st.sidebar.number_input("Refresh interval (secs)", min_value=10, max_value=3600, value=60)

# Email Alerts
email_alert = st.sidebar.checkbox("📧 Enable Email Alert")
recipient_email = st.sidebar.text_input("Recipient Email") if email_alert else None

# API keys
alpha_key = "Z0ANCCQ81ZW5OVYZ"
finnhub_key = "cvrbc29r01qp88cpdph0cvrbc29r01qp88cpdphg"

# Excel Template Upload
template_file = st.sidebar.file_uploader("Upload Excel Template", type=[".xlsx"])

# Parse tickers
ticker_list = [t.strip().upper() for t in ticker_input.split(',') if t.strip()]

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
        candles = client.stock_candles(ticker, 'D', 1640995200, 1711929600)
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

# Load or initialize ticker history
history_file = "ticker_history.json"
if os.path.exists(history_file):
    with open(history_file, 'r') as f:
        ticker_history = json.load(f)
else:
    ticker_history = []

# Process tickers
def process_all():
    all_reports = []
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

        # Excel Fill and Chart
        if template_file:
            wb = load_workbook(io.BytesIO(template_file.read()), data_only=True)
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

            # Auto Chart inside Excel
            chart = LineChart()
            chart.title = "Historical Prices"
            if metrics.get("History") is not None:
                hist = metrics["History"].reset_index()
                hist['Date'] = hist['Date'].dt.strftime('%Y-%m-%d')
                for i, row in hist.iterrows():
                    ws.append([row['Date'], row['Close']])
                data_ref = Reference(ws, min_col=2, min_row=len(fill_map)+2, max_row=ws.max_row)
                cats_ref = Reference(ws, min_col=1, min_row=len(fill_map)+2, max_row=ws.max_row)
                chart.add_data(data_ref, titles_from_data=False)
                chart.set_categories(cats_ref)
                ws.add_chart(chart, f"D10")

            output = io.BytesIO()
            wb.save(output)
            st.download_button("📅 Download Updated Excel", data=output.getvalue(), file_name=f"{ticker}_updated.xlsx")

        # Save ticker history
        if ticker not in ticker_history:
            ticker_history.append(ticker)
            with open(history_file, 'w') as f:
                json.dump(ticker_history, f)

        all_reports.append(df)

    # Export to CSV
    csv_export = pd.concat(all_reports)
    st.download_button("⬇️ Export All Metrics as CSV", csv_export.to_csv(index=False), file_name="all_ticker_metrics.csv")

    # Send email
    if email_alert and recipient_email:
        try:
            msg = MIMEMultipart()
            msg['From'] = "your_email@example.com"
            msg['To'] = recipient_email
            msg['Subject'] = "Financial Report"

            body = "Attached is your latest financial data report."
            msg.attach(MIMEText(body, 'plain'))

            csv_part = MIMEBase('application', 'octet-stream')
            csv_data = csv_export.to_csv(index=False).encode('utf-8')
            csv_part.set_payload(csv_data)
            encoders.encode_base64(csv_part)
            csv_part.add_header('Content-Disposition', "attachment; filename=all_ticker_metrics.csv")
            msg.attach(csv_part)

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login("your_email@example.com", "your_email_password")
            server.send_message(msg)
            server.quit()
            st.success("📧 Email sent successfully!")
        except Exception as e:
            st.error(f"Failed to send email: {e}")

    st.success("✅ Done processing all tickers!")

if refresh:
    last_run = time.time()
    while time.time() - last_run < interval:
        process_all()
        time.sleep(interval)
else:
    if st.button("📅 Fetch Data"):
        process_all()

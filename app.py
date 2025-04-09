import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage

# Alpha Vantage key
ALPHA_VANTAGE_API_KEY = "Q8LU981EWC83K7VI"

# Cell mapping based on template
cell_map = {
    "Operating Income": "D8",
    "EBITDA": "D9",
    "Profit Before Tax": "D10",
    "Net Income": "D11",
    "EPS": "D12",
    "Cash Flow from Operations": "D13",
    "Free Cash Flow": "D14",
    "ROE": "D15",
    "ROCE": "D16",
    "Debt to Equity": "D17",
    "P/E": "D18"
}

def fetch_yahoo_finance_data(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info
    financials = ticker.financials
    cashflow = ticker.cashflow

    try:
        metrics = {
            "Operating Income": financials.loc["Operating Income"].iloc[0] / 1e6,
            "EBITDA": financials.loc["EBITDA"].iloc[0] / 1e6,
            "Profit Before Tax": financials.loc["Pretax Income"].iloc[0] / 1e6,
            "Net Income": financials.loc["Net Income"].iloc[0] / 1e6,
            "EPS": info.get("trailingEps", 0),
            "Cash Flow from Operations": cashflow.loc["Total Cash From Operating Activities"].iloc[0] / 1e6,
            "Free Cash Flow": (cashflow.loc["Total Cash From Operating Activities"].iloc[0] -
                               cashflow.loc["Capital Expenditures"].iloc[0]) / 1e6,
            "ROE": info.get("returnOnEquity", 0) * 100,
            "ROCE": info.get("returnOnAssets", 0) * 100,
            "Debt to Equity": info.get("debtToEquity", 0),
            "P/E": info.get("trailingPE", 0)
        }
        return metrics
    except Exception as e:
        st.error(f"Yahoo Finance data fetch failed: {e}")
        return {}

def fetch_alpha_vantage_data(ticker_symbol):
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker_symbol}&apikey={ALPHA_VANTAGE_API_KEY}"
    r = requests.get(url)
    data = r.json()

    try:
        metrics = {
            "Operating Income": float(data.get("OperatingIncome", 0)) / 1e6,
            "EBITDA": float(data.get("EBITDA", 0)) / 1e6,
            "Profit Before Tax": float(data.get("EBITDA", 0)) / 1e6 * 0.8,  # Est.
            "Net Income": float(data.get("NetIncomeTTM", 0)) / 1e6,
            "EPS": float(data.get("EPS", 0)),
            "Cash Flow from Operations": float(data.get("OperatingCashflowTTM", 0)) / 1e6,
            "Free Cash Flow": float(data.get("FreeCashFlowTTM", 0)) / 1e6,
            "ROE": float(data.get("ReturnOnEquityTTM", 0)),
            "ROCE": float(data.get("ReturnOnAssetsTTM", 0)),
            "Debt to Equity": float(data.get("DebtEquity", 0)),
            "P/E": float(data.get("PERatio", 0)),
        }
        return metrics
    except Exception as e:
        st.error(f"Alpha Vantage data fetch failed: {e}")
        return {}

def generate_bar_chart(metrics):
    fig, ax = plt.subplots(figsize=(8, 4))
    labels = list(metrics.keys())
    values = list(metrics.values())
    ax.barh(labels, values, color='skyblue')
    ax.set_title("Key Financial Metrics")
    plt.tight_layout()
    chart_io = BytesIO()
    plt.savefig(chart_io, format='png')
    chart_io.seek(0)
    return chart_io

def update_excel(template_file, metrics, chart_img):
    wb = load_workbook(template_file)
    ws = wb.active

    for metric, cell in cell_map.items():
        ws[cell] = round(metrics.get(metric, 0), 2)

    img = XLImage(chart_img)
    ws.add_image(img, "F8")

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

# ----------- Streamlit App -----------

st.set_page_config(page_title="Financial Model Generator", layout="wide")
st.title("📊 Automated Financial Model Tool")

col1, col2 = st.columns(2)
with col1:
    ticker = st.text_input("Enter Company Ticker (e.g., TTM for Tata Motors)", "TTM")
with col2:
    source = st.selectbox("Select Data Source", ["Yahoo Finance", "Alpha Vantage"])

template_file = st.file_uploader("📁 Upload Excel Template", type=["xlsx"])

if st.button("🔍 Generate Financial Model"):
    if not template_file:
        st.error("Please upload your Excel template.")
    else:
        st.info("Fetching data...")
        if source == "Yahoo Finance":
            metrics = fetch_yahoo_finance_data(ticker)
        else:
            metrics = fetch_alpha_vantage_data(ticker)

        if metrics:
            st.success("Data fetched and mapped successfully!")
            chart_img = generate_bar_chart(metrics)
            updated_excel = update_excel(template_file, metrics, chart_img)

            st.download_button(
                label="⬇️ Download Updated Excel",
                data=updated_excel,
                file_name="Updated_Financial_Model.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.image(chart_img, caption="Generated Financial Metrics Chart", use_column_width=True)

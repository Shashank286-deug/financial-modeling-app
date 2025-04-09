import streamlit as st
import yfinance as yf
import requests
import openpyxl
import matplotlib.pyplot as plt
import io
import tempfile
import pandas as pd
from openpyxl.drawing.image import Image

# API key for Alpha Vantage
ALPHA_VANTAGE_API_KEY = "Q8LU981EWC83K7VI"

st.set_page_config(page_title="📊 Financial Model Generator", layout="wide")

st.title("📊 Financial Model Generator")
st.markdown("Upload your Excel template, choose a company, and auto-fill the financial model with live data!")

# Step 1: Select data source
data_source = st.selectbox("Choose Data Source", ["Yahoo Finance", "Alpha Vantage"])

# Step 2: Enter ticker symbol
ticker = st.text_input("Enter Ticker Symbol (e.g., TATAMOTORS.BO, AAPL)", "TATAMOTORS.BO")

# Step 3: Upload Excel template
uploaded_file = st.file_uploader("Upload your Excel Template", type=["xlsx"])

def get_data_yahoo(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        return {
            "EPS": info.get("trailingEps", None),
            "EBITDA": info.get("ebitda", None),
            "P/E": info.get("trailingPE", None),
            "FreeCashFlow": info.get("freeCashflow", None),
            "MarketCap": info.get("marketCap", None)
        }
    except Exception as e:
        st.error(f"Error fetching from Yahoo Finance: {e}")
        return {}

def get_data_alpha(ticker):
    try:
        url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
        response = requests.get(url)
        data = response.json()

        return {
            "EPS": float(data.get("EPS", 0)),
            "EBITDA": float(data.get("EBITDA", 0)),
            "P/E": float(data.get("PERatio", 0)),
            "FreeCashFlow": float(data.get("FreeCashFlowPerShare", 0)) * float(data.get("SharesOutstanding", 1)),
            "MarketCap": float(data.get("MarketCapitalization", 0))
        }
    except Exception as e:
        st.error(f"Error fetching from Alpha Vantage: {e}")
        return {}

# Fetch data
if st.button("🔍 Fetch & Fill Data") and uploaded_file and ticker:
    st.info("Fetching data...")

    if data_source == "Yahoo Finance":
        financials = get_data_yahoo(ticker)
    else:
        financials = get_data_alpha(ticker)

    st.write("📈 Retrieved Data:", financials)

    if financials and uploaded_file:
        # Load template
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        wb = openpyxl.load_workbook(tmp_path)
        ws = wb.active  # Assume data is in first sheet

        # Define cell mappings (adjust as per your template)
        mappings = {
            "EPS": "B6",
            "EBITDA": "B7",
            "P/E": "B8",
            "FreeCashFlow": "B9",
            "MarketCap": "B10"
        }

        for key, cell in mappings.items():
            if key in financials and financials[key] is not None:
                try:
                    ws[cell] = financials[key]
                except Exception as e:
                    st.warning(f"Could not write {key} to {cell}: {e}")

        # Create visualization
        fig, ax = plt.subplots()
        labels = [k for k in financials if financials[k] is not None]
        values = [financials[k] for k in labels]
        ax.barh(labels, values, color="skyblue")
        ax.set_title(f"{ticker} Financial Snapshot")

        # Save plot as image
        image_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
        fig.savefig(image_path, bbox_inches='tight')

        # Insert chart in Excel
        img = Image(image_path)
        ws.add_image(img, "D6")  # Place wherever you want

        # Save final output
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx").name
        wb.save(output_path)

        # Provide download
        with open(output_path, "rb") as f:
            st.download_button("📥 Download Updated Excel", f, file_name="Updated_Model.xlsx")


import streamlit as st
import requests
from openpyxl import load_workbook
import tempfile
import shutil
import pandas as pd

API_KEY = "70UUKXWKAZTUH2D5"

def fetch_income_statement(symbol):
    url = f"https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={symbol}&apikey={API_KEY}"
    r = requests.get(url)
    data = r.json()
    return data.get("annualReports", [{}])[0], data.get("annualReports", [])[:5]

def fetch_global_quote(symbol):
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={API_KEY}"
    r = requests.get(url)
    data = r.json()
    return data.get("Global Quote", {})

def calculate_valuation_metrics(quote, financials):
    try:
        price = float(quote.get("05. price", 0))
        shares = int(financials.get("weightedAverageShsOut", "1"))
        eps = float(financials.get("eps", "0"))

        pe_ratio = price / eps if eps else 0
        market_cap = price * shares
        revenue = int(financials.get("totalRevenue", "0"))
        ps_ratio = market_cap / revenue if revenue else 0

        return {
            "P/E Ratio": round(pe_ratio, 2),
            "P/S Ratio": round(ps_ratio, 2),
            "Market Cap ($M)": round(market_cap / 1e6, 2),
            "Share Price ($)": round(price, 2)
        }
    except Exception as e:
        st.error(f"Error calculating valuation metrics: {e}")
        return {}
    

def fill_template(financials, template_path):
    temp_dir = tempfile.mkdtemp()
    new_path = f"{temp_dir}/Filled_Model.xlsx"
    shutil.copy(template_path, new_path)

    wb = load_workbook(new_path)
    sheet = wb.active

    try:
        sheet["B3"] = financials.get("totalRevenue", "N/A")
        sheet["B4"] = financials.get("netIncome", "N/A")
        sheet["B5"] = financials.get("eps", "N/A")
        sheet["B6"] = financials.get("ebitda", "N/A")
        sheet["B7"] = financials.get("operatingCashflow", "N/A")
    except Exception as e:
        print(f"Error filling cells: {e}")

    wb.save(new_path)
    return new_path

def get_chart_data(history):
    years = [r["fiscalDateEnding"][:4] for r in history]
    revenue = [int(r["totalRevenue"]) / 1e6 for r in history]
    income = [int(r["netIncome"]) / 1e6 for r in history]
    ebitda = [int(r.get("ebitda", 0)) / 1e6 for r in history]
    cashflow = [int(r.get("operatingCashflow", 0)) / 1e6 for r in history]
    return years[::-1], revenue[::-1], income[::-1], ebitda[::-1], cashflow[::-1]

# ---- Streamlit UI ----
st.set_page_config(layout="wide", page_title="Financial Modeling App")
st.title("💼 Auto Financial Modeling Tool")

symbol = st.text_input("Enter Stock Symbol", value="TATAMOTORS.BSE")
data_source = st.selectbox("Choose Data Source", ["Alpha Vantage"])  # Expandable

if symbol:
    financials, history = fetch_income_statement(symbol)
    quote = fetch_global_quote(symbol)

    if not financials:
        st.error("Couldn't fetch financial data.")
    else:
        tabs = st.tabs(["📊 Dashboard", "📁 Excel Model"])

        with tabs[0]:
            st.subheader(f"📊 Financial Dashboard: {symbol}")

            # --- Key Metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Revenue", f"${int(financials['totalRevenue'])/1e6:.2f} M")
            col2.metric("Net Income", f"${int(financials['netIncome'])/1e6:.2f} M")
            col3.metric("EPS", financials.get("eps", "N/A"))

            col4, col5 = st.columns(2)
            col4.metric("EBITDA", f"${int(financials.get('ebitda', 0))/1e6:.2f} M")
            col5.metric("Operating Cash Flow", f"${int(financials.get('operatingCashflow', 0))/1e6:.2f} M")

            # --- Valuation Metrics
            st.markdown("### 📈 Valuation Metrics")
            val_metrics = calculate_valuation_metrics(quote, financials)

            col6, col7, col8, col9 = st.columns(4)
            col6.metric("P/E Ratio", val_metrics.get("P/E Ratio", "N/A"))
            col7.metric("P/S Ratio", val_metrics.get("P/S Ratio", "N/A"))
            col8.metric("Market Cap ($M)", val_metrics.get("Market Cap ($M)", "N/A"))
            col9.metric("Share Price", f"${val_metrics.get('Share Price ($)', 'N/A')}")

            # --- Historical Chart
            years, revs, incomes, ebitdas, cashflows = get_chart_data(history)

            st.markdown("### 📉 Historical Financial Trends")
            st.line_chart(pd.DataFrame({
                "Revenue ($M)": revs,
                "Net Income ($M)": incomes,
                "EBITDA ($M)": ebitdas,
                "Operating Cash Flow ($M)": cashflows
            }, index=years))

        with tabs[1]:
            st.subheader("📁 Upload Excel Template to Fill")
            uploaded_file = st.file_uploader("Upload Template (.xlsx)", type=["xlsx"])

            if uploaded_file and st.button("🛠️ Generate Financial Model"):
                st.info("Processing...")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp.write(uploaded_file.read())
                    filled_path = fill_template(financials, tmp.name)

                with open(filled_path, "rb") as f:
                    st.success("Model ready! Download below 👇")
                    st.download_button("📥 Download Filled Model", f, file_name="Financial_Model_Filled.xlsx")

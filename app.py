import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import matplotlib.pyplot as plt
import io

# Set Streamlit layout
st.set_page_config(page_title="📊 Financial Dashboard", layout="wide")

# Constants
ALPHA_VANTAGE_API_KEY = "Q8LU981EWC83K7VI"

# Sidebar UI
st.sidebar.title("⚙️ Settings")
data_source = st.sidebar.selectbox("Choose Data Source", ["Yahoo Finance", "Alpha Vantage"])
ticker = st.sidebar.text_input("Enter Stock Ticker", value="AAPL")

uploaded_template = st.sidebar.file_uploader("📂 Upload Excel Template", type=["xlsx"])

# Functions
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
    if r.status_code != 200:
        return {}
    info = r.json()
    return {
        "P/E Ratio": info.get("PERatio", "N/A"),
        "EPS": info.get("EPS", "N/A"),
        "EBITDA": info.get("EBITDA", "N/A"),
        "Cash Flow": info.get("OperatingCashflow", "N/A"),
        "Revenue": info.get("RevenueTTM", "N/A")
    }

# Main
st.title("📊 Financial Dashboard with Excel Integration")

if st.button("📥 Fetch & Process Data"):
    with st.spinner("Loading data..."):
        if data_source == "Yahoo Finance":
            metrics = get_yahoo_data(ticker)
        else:
            metrics = get_alpha_data(ticker)

        if not metrics:
            st.error("Data fetch failed. Check ticker or try again.")
        else:
            st.subheader("📈 Valuation Metrics")
            df_metrics = pd.DataFrame(metrics.items(), columns=["Metric", "Value"])
            st.dataframe(df_metrics, use_container_width=True)

            # Visualize
            try:
                numeric_vals = {k: float(v) for k, v in metrics.items() if str(v).replace('.', '', 1).isdigit()}
                fig, ax = plt.subplots()
                ax.bar(numeric_vals.keys(), numeric_vals.values(), color='teal')
                ax.set_title(f"{ticker.upper()} Metrics")
                ax.set_ylabel("Value")
                plt.xticks(rotation=45)
                st.pyplot(fig)
            except Exception as e:
                st.warning(f"Could not generate chart: {e}")

            # Excel integration
            if uploaded_template:
                try:
                    df_excel = pd.read_excel(uploaded_template, sheet_name=None)
                    first_sheet_name = list(df_excel.keys())[0]
                    df_sheet = df_excel[first_sheet_name]

                    # Append metrics
                    metrics_df = pd.DataFrame(metrics.items(), columns=["Metric", "Value"])
                    updated_df = pd.concat([df_sheet, pd.DataFrame([[]]), metrics_df], ignore_index=True)

                    # Save to buffer
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        updated_df.to_excel(writer, index=False, sheet_name=first_sheet_name)
                    output.seek(0)

                    st.success("✅ Excel updated with new metrics!")
                    st.download_button("📩 Download Updated Excel", data=output, file_name="updated_model.xlsx")

                except Exception as e:
                    st.error(f"Excel update failed: {e}")
            else:
                st.warning("📎 Upload an Excel template to insert metrics.")

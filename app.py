import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import matplotlib.pyplot as plt
import io

# Streamlit page config
st.set_page_config(page_title="Financial Dashboard", layout="wide")

# Sidebar layout
st.sidebar.title("⚙️ Settings")
data_source = st.sidebar.selectbox("Choose Data Source", ["Yahoo Finance", "Alpha Vantage"])
ticker = st.sidebar.text_input("Stock Ticker (e.g. AAPL or TATAMOTORS.BO)", value="AAPL")
alpha_key = st.sidebar.text_input("Alpha Vantage API Key", value="Q8LU981EWC83K7VI")

# Upload Excel template
uploaded_template = st.sidebar.file_uploader("Upload Excel Template", type=["xlsx"])

# Function to fetch data from Yahoo Finance
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

# Function to fetch data from Alpha Vantage
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

# Main section
st.title("📊 Financial Dashboard with Excel Integration")

if st.button("🔍 Fetch & Process Data"):
    with st.spinner("Fetching data..."):
        # Choose API
        if data_source == "Yahoo Finance":
            metrics = get_yahoo_data(ticker)
        else:
            metrics = get_alpha_data(ticker, alpha_key)

        if not metrics:
            st.error("Could not retrieve financial data.")
        else:
            # Show metrics in a table
            st.subheader("💡 Valuation Metrics")
            df_metrics = pd.DataFrame(metrics.items(), columns=["Metric", "Value"])
            st.dataframe(df_metrics, use_container_width=True)

            # Chart
            numeric_vals = {k: v for k, v in metrics.items() if isinstance(v, (int, float))}
            if numeric_vals:
                fig, ax = plt.subplots()
                ax.bar(numeric_vals.keys(), numeric_vals.values(), color='skyblue')
                ax.set_title("Valuation Metrics")
                plt.xticks(rotation=45)
                st.pyplot(fig)

            # Excel Integration
            if uploaded_template:
                try:
                    df_excel = pd.read_excel(uploaded_template, sheet_name=None)

                    # Update first sheet with metrics
                    first_sheet_name = list(df_excel.keys())[0]
                    df_sheet = df_excel[first_sheet_name]

                    # Append metrics to the bottom of the sheet
                    metrics_df = pd.DataFrame(metrics.items(), columns=["Metric", "Value"])
                    new_sheet = pd.concat([df_sheet, pd.DataFrame([[]]), metrics_df], ignore_index=True)

                    # Write updated Excel to buffer
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        new_sheet.to_excel(writer, index=False, sheet_name=first_sheet_name)
                    output.seek(0)

                    st.success("✅ Metrics added to Excel successfully!")
                    st.download_button("📥 Download Updated Excel", data=output, file_name="updated_financial_model.xlsx")

                except Exception as e:
                    st.error(f"Error processing Excel file: {e}")
            else:
                st.warning("📎 Please upload an Excel template to embed the metrics.")

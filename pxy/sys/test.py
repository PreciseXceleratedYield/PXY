# init_csv.py
import yfinance as yf
import pandas as pd
import os
from syscnfgpxy import TICKER  # only ticker from config

# ---------------- CONFIG ----------------
CSV_PATH = os.path.join(os.path.dirname(__file__), "line_data.csv")  # sys/line_data.csv
INTERVAL = "1m"
PERIOD = "1d"
MIN_ROWS = 5  # ensure at least this many rows

# ---------------- FETCH DATA ----------------
def fetch_yf_data(period=PERIOD, interval=INTERVAL, ticker=TICKER):
    """Fetch latest historical data from Yahoo Finance."""
    try:
        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(period=period, interval=interval)
        if df.empty:
            print("No data fetched from Yahoo Finance.")
            return None
        # Keep only timestamp and close
        df = df[["Close"]].copy()
        # Convert index to UNIX timestamp
        df["time"] = df.index.astype("int64") // 10**9
        df = df[["time", "Close"]]
        # Ensure minimum rows
        if len(df) < MIN_ROWS:
            df = df.reindex(range(MIN_ROWS), method="ffill")
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

# ---------------- INITIAL CSV UPDATE ----------------
def init_csv():
    df = fetch_yf_data()
    if df is not None:
        df.to_csv(CSV_PATH, index=False)
        print(f"CSV initialized at {CSV_PATH} with {len(df)} rows.")
    else:
        print("CSV not created. No data available.")

# ---------------- RUN ----------------
if __name__ == "__main__":
    init_csv()

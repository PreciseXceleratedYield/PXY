# sysdtafpxy.py

import yfinance as yf
import pandas as pd
import os
from syscnfgpxy import TICKER  # only ticker from config

# Module-level defaults
DEFAULT_INTERVAL = "1m"
DEFAULT_MIN_ROWS = 5
CSV_FILE = "market_data.csv"


def fetch_yf_data(period="1d", interval=None, min_rows=None, ticker=None):
    """
    Fetch historical data for a ticker using yfinance.
    Falls back to 5-day history if insufficient rows.
    """
    interval = interval or DEFAULT_INTERVAL
    min_rows = min_rows or DEFAULT_MIN_ROWS
    ticker_symbol = ticker or TICKER

    ticker_obj = yf.Ticker(ticker_symbol)
    df = ticker_obj.history(period=period, interval=interval)
    df.dropna(inplace=True)

    # Fallback if insufficient rows
    if len(df) < min_rows:
        df = ticker_obj.history(period="5d", interval=interval)
        df.dropna(inplace=True)

    # Reset index to have 'Datetime' as a column
    df.reset_index(inplace=True)
    return df


def save_to_csv(df, file_path=CSV_FILE):
    """
    Save or append dataframe to CSV.
    - Creates file if not exists
    - Appends if exists
    - Removes duplicates based on Datetime
    """
    if not os.path.exists(file_path):
        df.to_csv(file_path, index=False)
        return

    # Read existing data
    existing_df = pd.read_csv(file_path)

    # Combine and drop duplicates
    combined_df = pd.concat([existing_df, df], ignore_index=True)

    if "Datetime" in combined_df.columns:
        combined_df.drop_duplicates(subset=["Datetime"], keep="last", inplace=True)

    # Save back
    combined_df.to_csv(file_path, index=False)


def get_latest_data():
    """
    Returns the latest row of data
    """
    df = fetch_yf_data(period="1d", interval=DEFAULT_INTERVAL)
    save_to_csv(df)  # <-- persist every call
    return df.tail(1)


# -------- Self-runnable test --------
if __name__ == "__main__":
    print("=== Testing Data Fetch Module ===")
    df = fetch_yf_data()
    save_to_csv(df)
    print(df.tail(5))

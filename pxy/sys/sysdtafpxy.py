# sysdtafpxy.py

import yfinance as yf
import pandas as pd
from syscnfgpxy import TICKER  # only ticker from config

# Module-level defaults
DEFAULT_INTERVAL = "1m"
DEFAULT_MIN_ROWS = 5

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

def get_latest_data():
    """
    Returns the latest row of data
    """
    df = fetch_yf_data(period="1d", interval=DEFAULT_INTERVAL)
    return df.tail(1)

# -------- Self-runnable test --------
if __name__ == "__main__":
    print("=== Testing Data Fetch Module ===")
    df = fetch_yf_data()
    print(df.tail(5))


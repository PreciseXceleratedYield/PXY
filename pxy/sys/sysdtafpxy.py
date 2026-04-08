# sysdtafpxy.py

import yfinance as yf
import pandas as pd
from syscnfgpxy import TICKER  # only ticker from config

# Module-level default
DEFAULT_INTERVAL = "1m"

def fetch_yf_data(period="1d", interval=None, ticker=None):
    """
    Fetch historical data for a ticker using yfinance.
    No minimum row check; returns exactly what yfinance gives.
    """
    interval = interval or DEFAULT_INTERVAL
    ticker_symbol = ticker or TICKER

    ticker_obj = yf.Ticker(ticker_symbol)
    df = ticker_obj.history(period=period, interval=interval)
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
    print(df.tail())  # prints last few rows for inspection

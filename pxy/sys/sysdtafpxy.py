# sysdtafpxy.py

import yfinance as yf
import pandas as pd
from syscnfgpxy import TICKER  # only ticker from config

# Module-level default
DEFAULT_INTERVAL = "1m"
DEFAULT_PERIOD = "5d"  # default fetch 5 days

def fetch_yf_data(period=None, interval=None, ticker=None):
    """
    Fetch historical data for a ticker using yfinance.
    By default, fetches 5 days of 1-minute data.
    """
    period = period or DEFAULT_PERIOD
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
    df = fetch_yf_data()
    return df.tail(1)

# -------- Self-runnable test --------
if __name__ == "__main__":
    print("=== Testing Data Fetch Module ===")
    df = fetch_yf_data()
    print(df.tail())  # prints last few rows for inspection

# sysdtafpxy.py

import yfinance as yf
import pandas as pd
from syscnfgpxy import TICKER  # only ticker from config

# Module-level defaults
DEFAULT_INTERVAL = "1m"


def fetch_yf_data(period="1d", interval=None, ticker=None):
    """
    Fetch historical data for a ticker using yfinance.
    Falls back to 5-day history if primary fetch fails or is empty.
    """
    interval = interval or DEFAULT_INTERVAL
    ticker_symbol = ticker or TICKER

    try:
        ticker_obj = yf.Ticker(ticker_symbol)

        # 1️⃣ PRIMARY FETCH
        df = ticker_obj.history(period=period, interval=interval)

        # 2️⃣ SAFETY CHECK (CRITICAL FIX)
        if df is None or df.empty:
            print(f"YF_EMPTY_PRIMARY|{ticker_symbol}")
            df = pd.DataFrame()

        # 3️⃣ CLEAN ONLY IF VALID
        if not df.empty:
            df.dropna(inplace=True)

        # 4️⃣ FALLBACK (always attempt if empty)
        if df is None or df.empty:
            fallback_df = ticker_obj.history(period="5d", interval=interval)

            if fallback_df is not None and not fallback_df.empty:
                fallback_df.dropna(inplace=True)
                df = fallback_df
            else:
                print(f"YF_FALLBACK_FAILED|{ticker_symbol}")

        # 5️⃣ FINAL GUARD
        if df is None or df.empty:
            print(f"YF_NO_DATA_FINAL|{ticker_symbol}")
            return pd.DataFrame()

        # 6️⃣ RESET INDEX
        df.reset_index(inplace=True)
        return df

    except Exception as e:
        print(f"YF_EXCEPTION|{ticker_symbol}|{str(e)}")
        return pd.DataFrame()


def get_latest_data():
    """
    Returns the latest row of data
    """
    df = fetch_yf_data(period="1d", interval=DEFAULT_INTERVAL)

    if df is None or df.empty:
        return pd.DataFrame()

    return df.tail(1)


# -------- Self-runnable test --------
if __name__ == "__main__":
    print("=== Testing Data Fetch Module ===")
    df = fetch_yf_data()

    if df is None or df.empty:
        print("NO DATA RECEIVED")
    else:
        print(df.tail(5))

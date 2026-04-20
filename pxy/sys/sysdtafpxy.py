# sysdtafpxy.py

import yfinance as yf
import pandas as pd
from syscnfgpxy import TICKER  # only ticker from config

DEFAULT_INTERVAL = "1m"


def fetch_yf_data(period="1d", interval=None, ticker=None):
    interval = interval or DEFAULT_INTERVAL
    ticker_symbol = ticker or TICKER

    try:
        # 1️⃣ PRIMARY (better than Ticker().history for indices)
        df = yf.download(
            tickers=ticker_symbol,
            period=period,
            interval=interval,
            progress=False,
            threads=False
        )

        # 2️⃣ fallback attempt if empty
        if df is None or df.empty:
            print(f"YF_PRIMARY_FAIL|{ticker_symbol}")

            df = yf.download(
                tickers=ticker_symbol,
                period="5d",
                interval=interval,
                progress=False,
                threads=False
            )

        # 3️⃣ final validation
        if df is None or df.empty:
            print(f"YF_TOTAL_FAILURE|{ticker_symbol}")
            return pd.DataFrame()

        df.dropna(inplace=True)

        # 4️⃣ reset index safely
        df.reset_index(inplace=True)

        return df

    except Exception as e:
        print(f"YF_EXCEPTION|{ticker_symbol}|{str(e)}")
        return pd.DataFrame()


def get_latest_data():
    df = fetch_yf_data(period="1d", interval=DEFAULT_INTERVAL)

    if df is None or df.empty:
        return pd.DataFrame()

    return df.tail(1)


# -------- Self test --------
if __name__ == "__main__":
    print("=== Testing Data Fetch Module ===")
    df = fetch_yf_data()

    if df is None or df.empty:
        print("NO DATA RECEIVED")
    else:
        print(df.tail(5))

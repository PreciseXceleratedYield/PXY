# run_exebbospxy.py

import yfinance as yf
import pandas as pd
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

# import your BOS engine
from exebbospxy import get_bos

DEBUG = True


# -------------------------------
# FETCH DATA (1m, 5d)
# -------------------------------
def fetch_data(symbol="NQ=F"):
    print(Fore.CYAN + f"\n📡 Fetching {symbol} 1m / 5d data...\n")

    df = yf.download(
        tickers=symbol,
        interval="1m",
        period="5d",
        progress=False
    )

    df.dropna(inplace=True)

    print(Fore.GREEN + f"✅ Data Loaded: {len(df)} rows\n")
    return df


# -------------------------------
# LIVE SIMULATION RUNNER
# -------------------------------
def run_bos(df):
    print(Fore.YELLOW + "🚀 Running BOS Engine...\n")

    for i in range(50, len(df)):  # start after warmup
        sub_df = df.iloc[:i].copy()

        signal = get_bos(sub_df)

        last_row = sub_df.iloc[-1]

        if DEBUG:
            print(
                f"{Fore.WHITE}{last_row.name} | "
                f"O:{last_row['Open']:.2f} "
                f"H:{last_row['High']:.2f} "
                f"L:{last_row['Low']:.2f} "
                f"C:{last_row['Close']:.2f} "
                f"➡ {Fore.MAGENTA}{signal}"
            )


# -------------------------------
# MAIN
# -------------------------------
if __name__ == "__main__":

    # 🔥 CHANGE SYMBOL HERE
    symbol = "NQ=F"   # NASDAQ futures (recommended for 24h testing)
    # symbol = "US100"  # sometimes works depending on broker mapping

    df = fetch_data(symbol)

    run_bos(df)

import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
import numpy as np

# =====================================
# CONFIG
# =====================================
SYMBOL = "^NSEI"
INTERVAL = "1m"
PERIOD = "5d"

# =====================================
# FETCH DATA
# =====================================
def fetch_data():
    ticker = yf.Ticker(SYMBOL)
    df = ticker.history(period=PERIOD, interval=INTERVAL)

    if df.empty:
        raise ValueError("No data fetched from Yahoo Finance.")

    for col in ["Open", "High", "Low", "Close"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df.index = df.index.tz_localize(None)
    return df.copy()

# =====================================
# ADD INDICATORS
# =====================================
def add_indicators(df):
    df["HA_Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4

    ha_open = [(df.iloc[0]["Open"] + df.iloc[0]["Close"]) / 2]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + df.iloc[i-1]["HA_Close"]) / 2)
    df["HA_Open"] = ha_open

    df["HA_High"] = df[["High", "HA_Open", "HA_Close"]].max(axis=1)
    df["HA_Low"] = df[["Low", "HA_Open", "HA_Close"]].min(axis=1)

    df["HA_Status"] = np.where(df["HA_Close"] > df["HA_Open"], "Bull", "Bear")

    return df.dropna()

# =====================================
# ENTRY + EXIT SIGNAL
# =====================================
def get_entry_signal():
    try:
        df = fetch_data()
        df = add_indicators(df)
    except Exception as e:
        return f"Error fetching data: {e}"

    if len(df) < 3:
        return "Not enough data", "Not enough data"

    last = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3]

    # ---------- Entry Logic ----------
    price_last = last["Open"]
    price_prev = prev["Open"]
    price_prev2 = prev2["Open"]

    ha_last = last["HA_Status"]
    ha_prev = prev["HA_Status"]

    if ha_prev == "Bear" and ha_last == "Bull":
        if price_prev2 > price_prev < price_last:
            entry_signal = "SBuy"
        else:
            entry_signal = "Bull"
    elif ha_prev == "Bull" and ha_last == "Bear":
        if price_prev2 < price_prev > price_last:
            entry_signal = "SSell"
        else:
            entry_signal = "Bear"
    else:
        if price_last > price_prev > price_prev2:
            entry_signal = "Bull"
        elif price_last < price_prev < price_prev2:
            entry_signal = "Bear"
        elif price_prev2 > price_prev < price_last:
            entry_signal = "SBuy"
        elif price_prev2 < price_prev > price_last:
            entry_signal = "SSell"
        else:
            entry_signal = "Bull" if price_last >= price_prev else "Bear"

    # ---------- Exit Logic ----------
    ha_high_last = last["HA_High"]
    ha_high_prev = prev["HA_High"]
    ha_high_prev2 = prev2["HA_High"]

    ha_low_last = last["HA_Low"]
    ha_low_prev = prev["HA_Low"]
    ha_low_prev2 = prev2["HA_Low"]

    if ha_high_last > ha_high_prev > ha_high_prev2:
        exit_signal = "Bull"
    elif ha_high_prev2 > ha_high_prev < ha_high_last:
        exit_signal = "SBuy"
    elif ha_low_last < ha_low_prev < ha_low_prev2:
        exit_signal = "Bear"
    elif ha_low_prev2 < ha_low_prev > ha_low_last:
        exit_signal = "SSell"
    else:
        exit_signal = "Bull" if ha_high_last >= ha_high_prev else "Bear"

    return entry_signal, exit_signal

# =====================================
# SELF TEST
# =====================================
if __name__ == "__main__":
    entry_signal, exit_signal = get_entry_signal()
    print("================================")
    print(f"Symbol       : {SYMBOL}")
    print(f"Entry Signal : {entry_signal}")
    print(f"Exit  Signal : {exit_signal}")
    print("================================")

# sysdeptpxy.py

# -------------------- IMPORTS --------------------
import pandas as pd
from sysdtafpxy import fetch_yf_data


# -------------------- CORE FUNCTION --------------------
def get_candle_visual(df=None, last_n=21):
    """
    Returns emoji string based on Heikin Ashi candles:
    🟢 bullish
    🔴 bearish
    """

    # -------- FETCH DATA --------
    if df is None:
        df = fetch_yf_data()

    if df is None or df.empty:
        return ""

    df.columns = [c.lower() for c in df.columns]

    # -------- HEIKIN ASHI --------
    ha_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = ha_close.copy()

    for i in range(len(df)):
        if i == 0:
            ha_open.iloc[i] = (df["open"].iloc[i] + df["close"].iloc[i]) / 2
        else:
            ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2

    # -------- COLOR --------
    colors = [
        "🟢" if ha_close.iloc[i] >= ha_open.iloc[i] else "🔴"
        for i in range(len(ha_close))
    ]

    return "".join(colors[-last_n:])


# -------------------- MAIN --------------------
def main():
    print(get_candle_visual())


if __name__ == "__main__":
    main()

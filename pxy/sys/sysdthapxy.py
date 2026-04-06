# sysdthapxy.py

import pandas as pd
from sysdtafpxy import fetch_yf_data

# 🔥 CONTROL: Keep forming candle INCLUDED
USE_FORMING_CANDLE = True


def get_ha_data(tickerSymbol=None, df=None):
    """
    Compute Heikin-Ashi OHLC and colors from data.

    - Uses forming (current) candle if available
    - If df is None, fetch from fetch_yf_data()

    Returns:
        ha_close (pd.Series)
        ha_open  (pd.Series)
        ha_color (pd.Series)
        df       (pd.DataFrame)
    """

    # ---------------- FETCH DATA ----------------
    if df is None:
        df = fetch_yf_data()

    if df is None or df.empty:
        return None, None, None, df

    # ---------------- OPTIONAL FILTER ----------------
    # (kept for flexibility, but OFF as per your requirement)
    if not USE_FORMING_CANDLE:
        df = df.iloc[:-1]

    # ---------------- HEIKIN-ASHI CALC ----------------

    # HA Close
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

    # HA Open
    ha_open = pd.Series(index=ha_close.index, dtype='float64')
    ha_open.iloc[0] = df['Open'].iloc[0]

    for i in range(1, len(ha_close)):
        ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2

    # HA Color (CORRECT LOGIC)
    ha_color = pd.Series(index=ha_close.index, dtype='object')

    for i in range(len(ha_close)):
        if ha_close.iloc[i] >= ha_open.iloc[i]:
            ha_color.iloc[i] = "green"
        else:
            ha_color.iloc[i] = "red"

    # ---------------- RETURN ----------------
    return ha_close, ha_open, ha_color, df


# ---------------- SELF TEST ----------------
if __name__ == "__main__":
    ha_close, ha_open, ha_color, df = get_ha_data()

    print("\n" + "="*50)
    print("HEIKIN-ASHI DEBUG (FORMING CANDLE ENABLED)")
    print("="*50)

    print("\nLast 5 HA Close:")
    print(ha_close.tail())

    print("\nLast 5 HA Open:")
    print(ha_open.tail())

    print("\nLast 5 HA Colors:")
    print(ha_color.tail())

    print("\nLast Candle Status:")
    print(f"HA Close : {ha_close.iloc[-1]}")
    print(f"HA Open  : {ha_open.iloc[-1]}")
    print(f"HA Color : {ha_color.iloc[-1]}")

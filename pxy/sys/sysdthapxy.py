# sysdthapxy.py

import pandas as pd
from sysdtafpxy import fetch_yf_data

def get_ha_data(tickerSymbol=None, df=None):
    """
    Compute Heikin-Ashi OHLC and colors from data.
    - If df is None, fetch from fetch_yf_data()
    Returns: ha_close, ha_open, ha_color, df
    """
    if df is None:
        df = fetch_yf_data()
    if df.empty:
        return None, None, None, df

    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = pd.Series(index=ha_close.index)
    ha_open.iloc[0] = df['Open'].iloc[0]
    for i in range(1, len(ha_close)):
        ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2

    ha_color = pd.Series("green", index=ha_close.index)
    ha_color.iloc[1:] = [
        "green" if ha_close.iloc[i] > ha_close.iloc[i-1] else "red"
        for i in range(1, len(ha_close))
    ]

    return ha_close, ha_open, ha_color, df

# Self-test
if __name__ == "__main__":
    ha_close, ha_open, ha_color, df = get_ha_data()
    print("Last 5 HA Close values:\n", ha_close.tail())
    print("Last 5 HA Colors:\n", ha_color.tail())

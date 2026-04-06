# sysdthapxy.py

import pandas as pd
from sysdtafpxy import fetch_yf_data

# 🔥 CONTROL: Keep forming candle INCLUDED
USE_FORMING_CANDLE = True


def get_ha_data(tickerSymbol=None, df=None):
    """
    Compute Heikin-Ashi OHLC and colors from data.

    Returns:
        ha_close (pd.Series)
        ha_open  (pd.Series)
        ha_color (pd.Series)
        df       (pd.DataFrame)
    """

    # ---------------- FETCH DATA ----------------
    if df is None:
        df = fetch_yf_data()
    else:
        df = df

    if df is None:
        return None, None, None, df
    elif df.empty:
        return None, None, None, df
    else:
        pass  # explicit

    # ---------------- FORMING CANDLE CONTROL ----------------
    if USE_FORMING_CANDLE is True:
        pass
    elif USE_FORMING_CANDLE is False:
        df = df.iloc[:-1]
    else:
        # invalid config
        return None, None, None, df

    # ---------------- VALIDATE REQUIRED COLUMNS ----------------
    required_cols = ['Open', 'High', 'Low', 'Close']

    for col in required_cols:
        if col not in df.columns:
            return None, None, None, df
        else:
            pass

    # ---------------- HEIKIN-ASHI CLOSE ----------------
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

    # ---------------- HEIKIN-ASHI OPEN ----------------
    ha_open = pd.Series(index=ha_close.index, dtype='float64')

    if len(ha_close) == 0:
        return None, None, None, df
    elif len(ha_close) > 0:
        ha_open.iloc[0] = df['Open'].iloc[0]
    else:
        return None, None, None, df

    for i in range(1, len(ha_close)):
        prev_open = ha_open.iloc[i - 1]
        prev_close = ha_close.iloc[i - 1]

        if pd.isna(prev_open) or pd.isna(prev_close):
            ha_open.iloc[i] = prev_open  # explicit fallback
        else:
            ha_open.iloc[i] = (prev_open + prev_close) / 2

    # ---------------- HEIKIN-ASHI COLOR ----------------
    ha_color = pd.Series(index=ha_close.index, dtype='object')

    for i in range(len(ha_close)):
        hc = ha_close.iloc[i]
        ho = ha_open.iloc[i]

        if pd.isna(hc) or pd.isna(ho):
            ha_color.iloc[i] = "neutral"
        elif hc > ho:
            ha_color.iloc[i] = "green"
        elif hc < ho:
            ha_color.iloc[i] = "red"
        elif hc == ho:
            ha_color.iloc[i] = "doji"
        else:
            ha_color.iloc[i] = "unknown"  # absolute fallback

    # ---------------- FINAL VALIDATION ----------------
    if ha_close is None:
        return None, None, None, df
    elif ha_open is None:
        return None, None, None, df
    elif ha_color is None:
        return None, None, None, df
    else:
        pass

    return ha_close, ha_open, ha_color, df


# ---------------- SELF TEST ----------------
if __name__ == "__main__":
    ha_close, ha_open, ha_color, df = get_ha_data()

    print("\n" + "="*60)
    print("STRICT HEIKIN-ASHI DEBUG (NO ASSUMPTIONS)")
    print("="*60)

    if ha_close is None:
        print("HA calculation failed")
    else:
        print("\nLast 5 HA Close:")
        print(ha_close.tail())

        print("\nLast 5 HA Open:")
        print(ha_open.tail())

        print("\nLast 5 HA Colors:")
        print(ha_color.tail())

        print("\nLast Candle Breakdown:")
        print(f"HA Close : {ha_close.iloc[-1]}")
        print(f"HA Open  : {ha_open.iloc[-1]}")
        print(f"HA Color : {ha_color.iloc[-1]}")

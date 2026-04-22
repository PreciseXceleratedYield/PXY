# sysdthapxy.py

import pandas as pd
from sysdtafpxy import fetch_yf_data

# 🔥 CONTROL: Keep forming candle INCLUDED (DO NOT BREAK DOWNSTREAM)
USE_FORMING_CANDLE = True

# 🔥 CLEAN SWITCH
# "HA"  → Heikin Ashi
# "OC2" → (Open + Close)/2 vs previous
CANDLE_STYLE = "HA"


def get_ha_data(tickerSymbol=None, df=None):
    """
    Compute Heikin-Ashi OHLC and colors from data.
    """

    if df is None:
        df = fetch_yf_data()

    if df is None or df.empty:
        return None, None, None, df

    if USE_FORMING_CANDLE is False:
        df = df.iloc[:-1]

    required_cols = ['Open', 'High', 'Low', 'Close']
    for col in required_cols:
        if col not in df.columns:
            return None, None, None, df

    # ---------------- HEIKIN-ASHI CLOSE ----------------
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

    # ---------------- HEIKIN-ASHI OPEN ----------------
    ha_open = pd.Series(index=ha_close.index, dtype='float64')

    if len(ha_close) == 0:
        return None, None, None, df

    ha_open.iloc[0] = df['Open'].iloc[0]

    for i in range(1, len(ha_close)):
        ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2

    # ---------------- OC2 ----------------
    oc2 = (df['Open'] + df['Close']) / 2
    oc2_prev = oc2.shift(1)

    # ---------------- COLOR ----------------
    ha_color = pd.Series(index=ha_close.index, dtype='object')

    for i in range(len(ha_close)):
        hc = ha_close.iloc[i]
        ho = ha_open.iloc[i]

        if USE_FORMING_CANDLE and i == len(ha_close) - 1:
            ha_color.iloc[i] = "none"
            continue

        if pd.isna(hc) or pd.isna(ho):
            ha_color.iloc[i] = "none"
            continue

        if CANDLE_STYLE == "OC2":
            oc = oc2.iloc[i]
            oc_prev_val = oc2_prev.iloc[i]

            if oc > oc_prev_val:
                ha_color.iloc[i] = "green"
            elif oc < oc_prev_val:
                ha_color.iloc[i] = "red"
            else:
                ha_color.iloc[i] = ha_color.iloc[i - 1] if i > 0 else "none"

        else:
            if hc > ho:
                ha_color.iloc[i] = "green"
            elif hc < ho:
                ha_color.iloc[i] = "red"
            else:
                ha_color.iloc[i] = ha_color.iloc[i - 1] if i > 0 else "none"

    return ha_close, ha_open, ha_color, df


# ==================================================
# 🔥 SIGNAL ENGINE
# ==================================================
def get_bull_bear_signal(ha_color: pd.Series):
    if ha_color is None:
        return None

    signal = pd.Series(index=ha_color.index, dtype='object')

    for i in range(len(ha_color)):
        curr = ha_color.iloc[i]

        if curr == "none" or pd.isna(curr):
            signal.iloc[i] = "NONE"
            continue

        prev = ha_color.iloc[i - 1] if i > 0 else None

        if prev == "red" and curr == "green":
            signal.iloc[i] = "BUY"

        elif prev == "green" and curr == "red":
            signal.iloc[i] = "SELL"

        elif curr == "green":
            signal.iloc[i] = "BULL"

        elif curr == "red":
            signal.iloc[i] = "BEAR"

        else:
            signal.iloc[i] = "NONE"

    return signal


# ==================================================
# 🔥 MAIN RUN BLOCK
# ==================================================
if __name__ == "__main__":

    ha_close, ha_open, ha_color, df = get_ha_data()
    signal = get_bull_bear_signal(ha_color)

    print("\n================ LAST 15 SIGNALS ================\n")
    if signal is not None:
        print(signal.tail(15))
    else:
        print("No signal generated")

    print("\n================ LAST COLOR STATE ================\n")
    if ha_color is not None:
        print(ha_color.tail(15))

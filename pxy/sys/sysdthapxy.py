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

    Returns:
        ha_close (pd.Series)
        ha_open  (pd.Series)
        ha_color (pd.Series) -> "green" / "red" / "none"
        df       (pd.DataFrame)
    """

    # ---------------- FETCH DATA ----------------
    if df is None:
        df = fetch_yf_data()

    if df is None or df.empty:
        return None, None, None, df

    # ---------------- FORMING CANDLE CONTROL ----------------
    if USE_FORMING_CANDLE is True:
        pass
    elif USE_FORMING_CANDLE is False:
        df = df.iloc[:-1]
    else:
        return None, None, None, df

    # ---------------- VALIDATE REQUIRED COLUMNS ----------------
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
        prev_open = ha_open.iloc[i - 1]
        prev_close = ha_close.iloc[i - 1]
        ha_open.iloc[i] = (prev_open + prev_close) / 2

    # ---------------- OC2 (Open+Close)/2 ----------------
    oc2 = (df['Open'] + df['Close']) / 2
    oc2_prev = oc2.shift(1)

    # ---------------- COLOR ----------------
    ha_color = pd.Series(index=ha_close.index, dtype='object')

    for i in range(len(ha_close)):
        hc = ha_close.iloc[i]
        ho = ha_open.iloc[i]

        oc = oc2.iloc[i]
        oc_prev_val = oc2_prev.iloc[i]

        # ==================================================
        # 🔥 EXCLUDE FORMING CANDLE FROM SIGNAL STATE
        # ==================================================
        if USE_FORMING_CANDLE is True and i == len(ha_close) - 1:
            ha_color.iloc[i] = "none"
            continue

        # ---------------- NA SAFETY ----------------
        if pd.isna(hc) or pd.isna(ho):
            ha_color.iloc[i] = "none"
            continue

        # ==================================================
        # 🔥 CLEAN SWITCH LOGIC (ONLY 2 MODES)
        # ==================================================

        if CANDLE_STYLE == "OC2":
            # 🔥 OC2 → current vs previous
            if oc > oc_prev_val:
                ha_color.iloc[i] = "green"
            elif oc < oc_prev_val:
                ha_color.iloc[i] = "red"
            else:
                if i == 0:
                    ha_color.iloc[i] = "none"
                else:
                    prev_color = ha_color.iloc[i - 1]
                    ha_color.iloc[i] = prev_color if prev_color in ["green", "red"] else "none"

        else:
            # 🔥 HA → original logic
            if hc > ho:
                ha_color.iloc[i] = "green"
            elif hc < ho:
                ha_color.iloc[i] = "red"
            else:
                if i == 0:
                    ha_color.iloc[i] = "none"
                else:
                    prev_color = ha_color.iloc[i - 1]
                    ha_color.iloc[i] = prev_color if prev_color in ["green", "red"] else "none"

    # ---------------- FINAL ----------------
    return ha_close, ha_open, ha_color, df

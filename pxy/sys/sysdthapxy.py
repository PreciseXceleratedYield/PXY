# sysdthapxy.py

import pandas as pd
from sysdtafpxy import fetch_yf_data

USE_FORMING_CANDLE = True
CANDLE_STYLE = "HA"


def get_ha_data(tickerSymbol=None, df=None):

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

    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

    ha_open = pd.Series(index=ha_close.index, dtype='float64')

    if len(ha_close) == 0:
        return None, None, None, df

    ha_open.iloc[0] = df['Open'].iloc[0]

    for i in range(1, len(ha_close)):
        prev_open = ha_open.iloc[i - 1]
        prev_close = ha_close.iloc[i - 1]
        ha_open.iloc[i] = (prev_open + prev_close) / 2

    oc2 = (df['Open'] + df['Close']) / 2
    oc2_prev = oc2.shift(1)

    ha_color = pd.Series(index=ha_close.index, dtype='object')

    for i in range(len(ha_close)):

        hc = ha_close.iloc[i]
        ho = ha_open.iloc[i]

        oc = oc2.iloc[i]
        oc_prev_val = oc2_prev.iloc[i]

        # ==================================================
        # 🔥 FIX: LAST CANDLE IS NOW NORMAL (NO EXCLUSION)
        # ==================================================

        if pd.isna(hc) or pd.isna(ho):
            ha_color.iloc[i] = "none"
            continue

        if CANDLE_STYLE == "OC2":

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

    return ha_close, ha_open, ha_color, df

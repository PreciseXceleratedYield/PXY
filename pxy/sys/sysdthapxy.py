import pandas as pd
from sysdtafpxy import fetch_yf_data

USE_FORMING_CANDLE = True
CANDLE_STYLE = "HA"


def get_ha_data(tickerSymbol=None, df=None):

    if df is None:
        df = fetch_yf_data()

    if df is None or df.empty:
        return None, None, None, df

    if not USE_FORMING_CANDLE:
        df = df.iloc[:-1]

    required_cols = ['Open', 'High', 'Low', 'Close']
    for col in required_cols:
        if col not in df.columns:
            return None, None, None, df

    # ==================================================
    # 🔥 HEIKIN ASHI CORE (CLEAN + CORRECT)
    # ==================================================

    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

    ha_open = pd.Series(index=df.index, dtype='float64')
    ha_open.iloc[0] = df['Open'].iloc[0]

    for i in range(1, len(df)):
        ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2

    # ==================================================
    # 🔥 COLOR LOGIC (SIMPLE + STABLE)
    # ==================================================

    ha_color = pd.Series(index=df.index, dtype='object')

    for i in range(len(df)):

        if pd.isna(ha_open.iloc[i]) or pd.isna(ha_close.iloc[i]):
            ha_color.iloc[i] = "none"
            continue

        if ha_close.iloc[i] > ha_open.iloc[i]:
            ha_color.iloc[i] = "green"
        elif ha_close.iloc[i] < ha_open.iloc[i]:
            ha_color.iloc[i] = "red"
        else:
            ha_color.iloc[i] = ha_color.iloc[i - 1] if i > 0 else "none"

    return ha_close, ha_open, ha_color, df

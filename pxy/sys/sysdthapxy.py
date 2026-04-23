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

    ha_close = (df['Open'] + df['Close']) / 2

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

    # ==================================================
    # 🔥 SIGNAL ENGINE (2 CANDLE HOLD + PATTERN LOGIC)
    # ==================================================

    signal = pd.Series(index=df.index, dtype='object')

    last_signal = None
    hold_count = 0

    for i in range(len(df)):

        if i < 1:
            signal.iloc[i] = "none"
            continue

        c0 = ha_color.iloc[i]
        c1 = ha_color.iloc[i - 1]
        c2 = ha_color.iloc[i - 2] if i >= 2 else None

        new_signal = None

        # ---------------- BUY LOGIC ----------------
        if c1 == "red" and c0 == "green":
            new_signal = "BUY"

        elif c2 == "red" and c1 == "green" and c0 == "green":
            new_signal = "BUY"

        elif c2 == "green" and c1 == "green" and c0 == "green":
            new_signal = "BULL"

        # ---------------- SELL LOGIC ----------------
        elif c1 == "green" and c0 == "red":
            new_signal = "SELL"

        elif c2 == "green" and c1 == "red" and c0 == "red":
            new_signal = "SELL"

        elif c2 == "red" and c1 == "red" and c0 == "red":
            new_signal = "BEAR"

        # ---------------- HOLD LOGIC ----------------
        if new_signal:
            last_signal = new_signal
            hold_count = 2
            signal.iloc[i] = new_signal

        elif hold_count > 0:
            signal.iloc[i] = last_signal
            hold_count -= 1

        else:
            signal.iloc[i] = "none"

    # 👇 inject into df (NO signature change)
    df["ha_signal"] = signal

    return ha_close, ha_open, ha_color, df

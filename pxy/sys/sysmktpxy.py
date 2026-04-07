# syscndlpxy.py

import pandas as pd
from sysdtafpxy import fetch_yf_data

# -------------------- CONFIG --------------------
CANDLE_MODE = "hacv"   # "cv" / "ha" / "hacv"
USE_FORMING_CANDLE = True


# -------------------- DATA SOURCE --------------------
def _get_close_series(df=None):

    if df is None:
        df = fetch_yf_data()

    if df is None or df.empty or 'Close' not in df.columns:
        return None, None, df

    if not USE_FORMING_CANDLE:
        df = df.iloc[:-1]

    cv_close = df['Close']
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

    return cv_close, ha_close, df


# -------------------- 3-CANDLE SIGNAL --------------------
def _detect_signal(close: pd.Series):

    if close is None or len(close) < 3:
        return "NONE"

    c1 = close.iloc[-1]
    c2 = close.iloc[-2]
    c3 = close.iloc[-3]

    # 🔺 Inverted V → SELL
    if c3 < c2 > c1:
        return "SELL"

    # 🔻 V → BUY
    if c3 > c2 < c1:
        return "BUY"

    # Trend
    if c1 > c2 > c3:
        return "BULL"

    if c1 < c2 < c3:
        return "BEAR"

    return "NONE"


# -------------------- DEPTH ENGINE --------------------
def _compute_depth(close: pd.Series):

    if close is None or len(close) < 2:
        return 1, 1, 1

    directions = []

    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            directions.append("up")
        elif close.iloc[i] < close.iloc[i-1]:
            directions.append("down")
        else:
            directions.append("flat")

    if not directions:
        return 1, 1, 1

    # -------- CURRENT --------
    current = directions[-1]

    # -------- CURRENT DEPTH --------
    current_depth = 0
    for d in reversed(directions):
        if d == current:
            current_depth += 1
        else:
            break

    # -------- PAST DEPTH --------
    past_depth = 0
    for d in reversed(directions[:-current_depth]):
        if d != current:
            past_depth += 1
        else:
            break

    past_depth = max(past_depth, 1)

    # -------- CE / PE --------
    if current == "up":
        ce_depth = max(current_depth, 1)
        pe_depth = 1

    elif current == "down":
        pe_depth = max(current_depth, 1)
        ce_depth = 1

    else:
        ce_depth = 1
        pe_depth = 1

    return past_depth, ce_depth, pe_depth


# -------------------- MAIN API --------------------
def detect_ha_flip_signal(df=None):
    """
    FINAL ENGINE

    Returns:
        signal, past_depth, ce_depth, pe_depth
    """

    cv_close, ha_close, df = _get_close_series(df)

    if cv_close is None:
        return "NONE", 1, 1, 1

    # -------- MODE SWITCH --------
    if CANDLE_MODE == "cv":
        close = cv_close
        signal = _detect_signal(close)

    elif CANDLE_MODE == "ha":
        close = ha_close
        signal = _detect_signal(close)

    elif CANDLE_MODE == "hacv":
        sig_cv = _detect_signal(cv_close)
        sig_ha = _detect_signal(ha_close)

        if sig_cv == sig_ha:
            signal = sig_cv
        else:
            signal = "NONE"

        close = cv_close  # depth always from CV (faster truth)

    else:
        raise ValueError("Invalid CANDLE_MODE")

    # -------- DEPTH --------
    past_depth, ce_depth, pe_depth = _compute_depth(close)

    return signal, past_depth, ce_depth, pe_depth


# -------------------- SELF TEST --------------------
if __name__ == "__main__":

    signal, past, ce, pe = detect_ha_flip_signal()

    print("\n" + "="*60)
    print("FINAL CANDLE ENGINE")
    print("="*60)

    print(f"Mode   : {CANDLE_MODE.upper()}")
    print(f"Signal : {signal}")
    print(f"Past   : {past}")
    print(f"CE     : {ce}")
    print(f"PE     : {pe}")

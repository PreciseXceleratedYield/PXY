# syssuperpxy.py

import pandas as pd
from sysdtafpxy import fetch_yf_data
from syscnfgpxy import PARAMS


def calculate_supertrend(df: pd.DataFrame, period=None, multiplier=None) -> pd.DataFrame:
    """
    Continuous SuperTrend (Pine-matching logic)
    - No jumps
    - Smooth trailing
    - Exact match with Pine version
    """

    period = period or PARAMS["supertrend_period"]   # 3
    multiplier = multiplier or PARAMS["supertrend_multiplier"]  # 3

    # -------- TRUE RANGE --------
    df['previous_close'] = df['Close'].shift(1)

    df['TR'] = df[['High', 'Low', 'Close', 'previous_close']].apply(
        lambda row: max(
            row['High'] - row['Low'],
            abs(row['High'] - row['previous_close']),
            abs(row['Low'] - row['previous_close'])
        ),
        axis=1
    )

    # -------- ATR (IMPORTANT: MATCH PINE RMA) --------
    df['ATR'] = df['TR'].ewm(alpha=1/period, adjust=False).mean()

    # -------- HL2 --------
    df['HL2'] = (df['High'] + df['Low']) / 2

    # -------- INIT --------
    st = [0] * len(df)
    trend = [""] * len(df)

    # -------- LOOP --------
    for i in range(len(df)):

        hl2 = df['HL2'].iloc[i]
        atr = df['ATR'].iloc[i]

        upper = hl2 + multiplier * atr
        lower = hl2 - multiplier * atr

        # ---- FIRST ROW ----
        if i == 0 or pd.isna(atr):
            st[i] = hl2
            trend[i] = "UP"
            continue

        prev_st = st[i - 1]
        prev_trend = trend[i - 1]
        close = df['Close'].iloc[i]

        # -------- TREND (MATCH PINE) --------
        if close > prev_st:
            curr_trend = "UP"
        elif close < prev_st:
            curr_trend = "DOWN"
        else:
            curr_trend = prev_trend

        # -------- CONTINUOUS TRAILING (NO JERK) --------
        if curr_trend == "UP":
            st[i] = max(lower, prev_st)
        else:
            st[i] = min(upper, prev_st)

        trend[i] = curr_trend

    # -------- ASSIGN --------
    df['ST'] = st
    df['ST_Trend'] = trend

    # -------- CLEANUP --------
    df.drop(columns=['previous_close'], inplace=True)

    return df


# -------- SELF RUN --------
if __name__ == "__main__":
    from colorama import Fore, Style, init
    init(autoreset=True)

    df = fetch_yf_data()
    df = calculate_supertrend(df)

    last_row = df.iloc[-1]

    trend = last_row['ST_Trend']
    line_value = int(last_row['ST'])

    # ---- COLOR ----
    if trend == "UP":
        color = Fore.GREEN
    elif trend == "DOWN":
        color = Fore.RED
    else:
        color = Fore.WHITE

    # ---- DASHBOARD FORMAT (42 WIDTH) ----
    left = f"Super:{trend}"
    right = f"LINE:{line_value}"
    line = f"{left:<21}{right:>21}"

    print(f"{color}{line}{Style.RESET_ALL}")

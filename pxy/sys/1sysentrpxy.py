# ==================================================
# PRODUCTION TRADING ENGINE (CLEAN)
# PRICE ACTION + OC2 FLOW
# OUTPUT:
#   RETURN → (ENTRY, EXIT)
#   PRINT  → MODE ONLY
# ==================================================

from sysdtafpxy import fetch_yf_data
import pandas as pd


# ==================================================
# DATA
# ==================================================
def get_df():
    df = fetch_yf_data(period="1d", interval="1m")

    if df is None or len(df) < 20:
        return None

    df['Datetime'] = pd.to_datetime(df['Datetime'])
    return df.reset_index(drop=True)


# ==================================================
# HELPERS
# ==================================================
LOOKBACK = 5

def get_prev_high(df):
    return df['High'].shift(1).rolling(LOOKBACK).max().iloc[-1]

def get_prev_low(df):
    return df['Low'].shift(1).rolling(LOOKBACK).min().iloc[-1]

def is_bullish(c):
    return c['Close'] > c['Open']

def is_bearish(c):
    return c['Close'] < c['Open']


# ==================================================
# ENTRY ENGINE (PRICE ACTION ONLY)
# ==================================================
def entry_signal(df):

    last = df.iloc[-1]
    prev_high = get_prev_high(df)
    prev_low = get_prev_low(df)

    rng = last['High'] - last['Low']

    # -------------------------
    # LIQUIDITY SWEEP
    # -------------------------
    if rng > 0:
        if last['Low'] < prev_low and (last['Close'] - last['Low']) > rng * 0.5:
            return "BUY", "LIQUIDITY_SWEEP_BUY"

        if last['High'] > prev_high and (last['High'] - last['Close']) > rng * 0.5:
            return "SELL", "LIQUIDITY_SWEEP_SELL"

    # -------------------------
    # REVERSAL
    # -------------------------
    if last['Close'] > prev_high and is_bullish(last):
        return "BUY", "REVERSAL_BUY"

    if last['Close'] < prev_low and is_bearish(last):
        return "SELL", "REVERSAL_SELL"

    # -------------------------
    # CONTINUATION
    # -------------------------
    if last['High'] > prev_high and is_bullish(last):
        return "BUY", "CONTINUATION_BUY"

    if last['Low'] < prev_low and is_bearish(last):
        return "SELL", "CONTINUATION_SELL"

    # -------------------------
    # IMBALANCE
    # -------------------------
    if len(df) >= 3:
        c1 = df.iloc[-3]
        c2 = df.iloc[-2]
        c3 = df.iloc[-1]

        if c1['High'] < c3['Low'] and is_bullish(c2):
            return "BUY", "IMBALANCE_BUY"

        if c1['Low'] > c3['High'] and is_bearish(c2):
            return "SELL", "IMBALANCE_SELL"

    return "NONE", None


# ==================================================
# OC2 ENGINE (FLOW STATE)
# ==================================================
def exit_signal(df):

    oc2 = (df['Open'] + df['Close']) / 2

    prev2 = oc2.iloc[-3]
    prev1 = oc2.iloc[-2]
    curr  = oc2.iloc[-1]

    if prev1 <= prev2 and curr > prev1:
        return "BUY"

    if prev1 >= prev2 and curr < prev1:
        return "SELL"

    if curr > prev1:
        return "BULL"

    return "BEAR"


# ==================================================
# UPGRADE ENGINE
# ==================================================
def apply_upgrade(entry_state, entry_tag, oc_state):

    if entry_state == "BUY":
        return "BUY", entry_tag

    if entry_state == "SELL":
        return "SELL", entry_tag

    return oc_state, f"OC2_{oc_state}"


# ==================================================
# MASTER ENGINE
# ==================================================
def get_signal():

    df = get_df()
    if df is None:
        print("MODE: NO_DATA")
        return "NONE", "NONE"

    entry_state, entry_tag = entry_signal(df)
    exit_state = exit_signal(df)

    final_entry, final_exit = apply_upgrade(entry_state, entry_tag, exit_state)

    # =========================
    # MODE PRINT (ONLY ONCE)
    # =========================
    if entry_state in ["BUY", "SELL"]:
        print(f"MODE: {entry_tag}")
    else:
        print(f"MODE: OC2_{exit_state}")

    return final_entry, final_exit


# ==================================================
# RUN
# ==================================================
if __name__ == "__main__":
    entry, exit_ = get_signal()
    print("FINAL ENTRY:", entry)
    print("FINAL EXIT :", exit_)

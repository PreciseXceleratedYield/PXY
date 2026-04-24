# ==================================================
# 5-STATE DUAL ENGINE (FINAL CLEAN VERSION)
# PRICE ACTION + OC/2 FLOW
# OUTPUT:
# ENTRY → BUY / SELL / BULL / BEAR
# EXIT  → BUY / SELL / BULL / BEAR
# ==================================================

from sysdtafpxy import fetch_yf_data
import pandas as pd


# ==================================================
# DATA FETCH
# ==================================================
def get_df():
    df = fetch_yf_data(period="1d", interval="1m")
    if df is None or len(df) < 20:
        return None
    return df


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

def is_strong(c):
    rng = c['High'] - c['Low']
    body = abs(c['Close'] - c['Open'])
    return rng > 0 and body > rng * 0.6


# ==================================================
# ENTRY SIGNAL (PRICE ACTION)
# ==================================================
def entry_signal(df):

    last = df.iloc[-1]
    prev_high = get_prev_high(df)
    prev_low = get_prev_low(df)

    # 1. MORNING BREAKOUT
    if len(df) >= 6:
        orb_high = df['High'].iloc[:5].max()
        orb_low = df['Low'].iloc[:5].min()

        if is_strong(last):
            if last['Close'] > orb_high:
                return "BUY", "MORNING_BREAKOUT_BUY"
            if last['Close'] < orb_low:
                return "SELL", "MORNING_BREAKOUT_SELL"

    # 2. LIQUIDITY SWEEP
    rng = last['High'] - last['Low']
    if rng > 0:
        if last['Low'] < prev_low and (last['Close'] - last['Low']) > rng * 0.5:
            return "BUY", "LIQUIDITY_SWEEP_BUY"

        if last['High'] > prev_high and (last['High'] - last['Close']) > rng * 0.5:
            return "SELL", "LIQUIDITY_SWEEP_SELL"

    # 3. REVERSAL
    if last['Close'] > prev_high and is_bullish(last):
        return "BUY", "REVERSAL_BUY"

    if last['Close'] < prev_low and is_bearish(last):
        return "SELL", "REVERSAL_SELL"

    # 4. CONTINUATION
    if last['High'] > prev_high and is_bullish(last):
        return "BUY", "CONTINUATION_BUY"

    if last['Low'] < prev_low and is_bearish(last):
        return "SELL", "CONTINUATION_SELL"

    # 5. IMBALANCE
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
# OC/2 FLOW (4 STATES)
# ==================================================
def exit_signal(df):

    if df is None or len(df) < 3:
        return "BULL"

    oc2 = (df['Open'] + df['Close']) / 2

    prev2 = oc2.iloc[-3]
    prev1 = oc2.iloc[-2]
    curr  = oc2.iloc[-1]

    # FLIP
    if prev1 <= prev2 and curr > prev1:
        return "BUY"

    if prev1 >= prev2 and curr < prev1:
        return "SELL"

    # CONTINUATION
    if curr > prev1:
        return "BULL"

    if curr < prev1:
        return "BEAR"

    return "BULL"


# ==================================================
# UPGRADE ENGINE (NO FORCING)
# ==================================================
def apply_upgrade(entry_state, entry_tag, oc_state):

    # Strong signal → use it
    if entry_state == "BUY":
        return "BUY", entry_tag

    if entry_state == "SELL":
        return "SELL", entry_tag

    # No signal → pass OC2 as-is
    return oc_state, f"OC2_{oc_state}"


# ==================================================
# MASTER ENGINE
# ==================================================
def get_signal():

    try:
        df = get_df()
        if df is None:
            print("ENTRY MODE: DEFAULT")
            return "BULL", "BULL"

        entry_state, entry_tag = entry_signal(df)
        oc_state = exit_signal(df)

        final_state, final_tag = apply_upgrade(entry_state, entry_tag, oc_state)

        # 🔥 PRINT ENTRY MODE
        print(f"ENTRY MODE: {final_tag}")

        return final_state, oc_state

    except Exception as e:
        print("[ERROR]", e)
        return "BULL", "BULL"


# ==================================================
# RUN
# ==================================================
if __name__ == "__main__":
    entry, exit_ = get_signal()
    print("FINAL ENTRY:", entry)
    print("OC/2 STATE :", exit_)

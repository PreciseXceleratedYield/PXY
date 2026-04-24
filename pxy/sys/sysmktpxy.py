# ==================================================
# FINAL DUAL ENGINE (LOCKED VERSION - PRODUCTION SAFE)
# PRICE ACTION + OC/2 FLOW + SAFETY LAYERS
# OUTPUT:
# ENTRY → BUY / SELL / BULL / BEAR / NONE
# EXIT  → BUY / SELL / BULL / BEAR / NONE
# ==================================================

from sysdtafpxy import fetch_yf_data
import pandas as pd
from datetime import time


# ==================================================
# DATA FETCH
# ==================================================
def get_df():
    df = fetch_yf_data(period="1d", interval="1m")

    if df is None or len(df) < 20:
        return None

    df['Datetime'] = pd.to_datetime(df['Datetime'])

    # Keep only today
    today = df['Datetime'].dt.date.iloc[-1]
    df = df[df['Datetime'].dt.date == today]

    # Start from 9:16
    df = df[df['Datetime'].dt.time >= time(9, 16)]

    if len(df) < 5:
        return None

    return df.reset_index(drop=True)


# ==================================================
# SAFETY: OPEN BLOCK
# ==================================================
def is_open_block(current_time):
    try:
        return time(9, 14) <= current_time <= time(9, 16)
    except:
        return False


# ==================================================
# SAFETY: DATA VALIDATION
# ==================================================
def is_data_valid(df):

    try:
        if df is None or len(df) < 5:
            return False

        required = ["Open", "High", "Low", "Close"]

        for col in required:
            if col not in df.columns:
                return False

        last = df.iloc[-1]

        if last[required].isnull().any():
            return False

        if last["High"] < last["Low"]:
            return False

        if not (last["Low"] <= last["Open"] <= last["High"]):
            return False

        if not (last["Low"] <= last["Close"] <= last["High"]):
            return False

        if last[required].min() <= 0:
            return False

        return True

    except:
        return False


# ==================================================
# HELPERS (FIXED - NA SAFE)
# ==================================================
LOOKBACK = 5

def get_prev_high(df):
    val = df['High'].shift(1).rolling(LOOKBACK).max().iloc[-1]
    return val if pd.notna(val) else df['High'].iloc[-1]

def get_prev_low(df):
    val = df['Low'].shift(1).rolling(LOOKBACK).min().iloc[-1]
    return val if pd.notna(val) else df['Low'].iloc[-1]

def is_bullish(c):
    return c['Close'] > c['Open']

def is_bearish(c):
    return c['Close'] < c['Open']


# ==================================================
# ENTRY SIGNAL (PRICE ACTION)
# ==================================================
def entry_signal(df):

    last = df.iloc[-1]
    prev_high = get_prev_high(df)
    prev_low = get_prev_low(df)

    rng = last['High'] - last['Low']

    # LIQUIDITY SWEEP
    if rng > 0:
        if last['Low'] < prev_low and (last['Close'] - last['Low']) > rng * 0.5:
            return "BUY", "LIQUIDITY_SWEEP_BUY"

        if last['High'] > prev_high and (last['High'] - last['Close']) > rng * 0.5:
            return "SELL", "LIQUIDITY_SWEEP_SELL"

    # REVERSAL
    if last['Close'] > prev_high and is_bullish(last):
        return "BUY", "REVERSAL_BUY"

    if last['Close'] < prev_low and is_bearish(last):
        return "SELL", "REVERSAL_SELL"

    # CONTINUATION
    if last['High'] > prev_high and is_bullish(last):
        return "BUY", "CONTINUATION_BUY"

    if last['Low'] < prev_low and is_bearish(last):
        return "SELL", "CONTINUATION_SELL"

    # IMBALANCE
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
        return "NONE"

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

    if curr < prev1:
        return "BEAR"

    return "NONE"


# ==================================================
# UPGRADE ENGINE
# ==================================================
def apply_upgrade(entry_state, entry_tag, oc_state):

    if entry_state == "BUY":
        return "BUY", entry_tag

    if entry_state == "SELL":
        return "SELL", entry_tag

    return oc_state, oc_state


# ==================================================
# MASTER ENGINE
# ==================================================
def get_signal():

    try:
        df = get_df()
        if df is None:
            print("🚫 ENTRY MODE: NO_DATA 📉")
            return "NONE", "NONE"

        current_time = df.iloc[-1]['Datetime'].time()

        # Opening safety block
        if is_open_block(current_time):
            print("⏳ ENTRY MODE: OPENING_BLOCK 🛑")
            return "NONE", "NONE"

        # Data validation
        if not is_data_valid(df):
            print("⚠️ ENTRY MODE: BAD_DATA 🚫")
            return "NONE", "NONE"

        # Core logic
        entry_state, entry_tag = entry_signal(df)
        oc_state = exit_signal(df)

        final_state, final_tag = apply_upgrade(entry_state, entry_tag, oc_state)

        print(f"🔥 ENTRY MODE: {final_tag} ✔️🚀")

        return final_state, oc_state

    except Exception as e:
        print("[ERROR]", e)
        return "NONE", "NONE"


# ==================================================
# RUN
# ==================================================
if __name__ == "__main__":
    entry, exit_ = get_signal()
    print("FINAL ENTRY:", entry)
    print("OC/2 STATE :", exit_)

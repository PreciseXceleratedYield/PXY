# sysmktpxy.py
from sysdtafpxy import fetch_yf_data
import pandas as pd

# --- LAYER 1: PURE CLOSE ---
def get_l1_close(df):
    c2, c1, curr = df['Close'].iloc[-3], df['Close'].iloc[-2], df['Close'].iloc[-1]
    if c1 < c2 and curr > c1: return "BUY"
    if c1 > c2 and curr < c1: return "SELL"
    if curr > c1: return "BULL"
    if curr < c1: return "BEAR"
    return "NONE"

# --- LAYER 2: OC/2 ---
def get_l2_oc2(df):
    mid = (df['Open'] + df['Close']) / 2
    m2, m1, curr = mid.iloc[-3], mid.iloc[-2], mid.iloc[-1]
    if m1 < m2 and curr > m1: return "BUY"
    if m1 > m2 and curr < m1: return "SELL"
    if curr > m1: return "BULL"
    if curr < m1: return "BEAR"
    return "NONE"

# --- LAYER 3: HA ---
def get_l3_ha(df):
    ha_c = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_o = (df['Open'].shift(1) + df['Close'].shift(1)) / 2
    curr_o, curr_c = ha_o.iloc[-1], ha_c.iloc[-1]
    prev_o, prev_c = ha_o.iloc[-2], ha_c.iloc[-2]
    if prev_c < prev_o and curr_c > curr_o: return "BUY"
    if prev_c > prev_o and curr_c < curr_o: return "SELL"
    if curr_c > curr_o: return "BULL"
    if curr_c < curr_o: return "BEAR"
    return "NONE"

# --- LAYER 4: CASCADE ENTRY ---
def get_l4_entry(l1, l2, l3):
    if l3 == "BUY": return "BUY"
    if l3 == "SELL": return "SELL"
    if l3 == "BULL":
        if l1 == "BUY" or l2 == "BUY": return "BUY"
        return "BULL"
    if l3 == "BEAR":
        if l1 == "SELL" or l2 == "SELL": return "SELL"
        return "BEAR"
    if l3 == "NONE":
        if l2 == "BUY": return "BUY"
        if l2 == "SELL": return "SELL"
        if l2 == "BULL": return "BULL"
        if l2 == "BEAR": return "BEAR"
    if l3 == "NONE" and l2 == "NONE":
        if l1 == "BUY": return "BUY"
        if l1 == "SELL": return "SELL"
        if l1 == "BULL": return "BULL"
        if l1 == "BEAR": return "BEAR"
    return "NONE"

# ==================================================
# MASTER INTERFACE (SURGICAL FIX: ADDED df=None)
# ==================================================
def get_signal(df=None): 
    """
    Returns (Entry_Signal, Exit_Signal)
    Entry: L4 (HA-Lead Cascade)
    Exit: L2 (OC/2 Flow)
    """
    try:
        # Use passed df or fetch fresh
        if df is None:
            df = fetch_yf_data()
            
        if df is None or df.empty:
            return "NONE", "NONE"

        # 1. Generate independent signals
        l1 = get_l1_close(df)
        l2 = get_l2_oc2(df)
        l3 = get_l3_ha(df)

        # 2. Assign Role Logic
        entry_sig = get_l4_entry(l1, l2, l3)
        exit_sig = l2 # Exit is strictly based on OC/2 state

        return entry_sig, exit_sig

    except Exception as e:
        print(f"Signal Error: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    entry, exit_state = get_signal()
    print(f"FINAL RESULT -> ENTRY: {entry}, EXIT: {exit_state}")



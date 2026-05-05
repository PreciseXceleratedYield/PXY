# sysentrpxy.py
from sysmktpxy import get_signal # L1-L4 Cascade Engine
from syscnfgpxy import TICKER
from sysstrndpxy import get_signal as get_st_signal # Returns VWAP as st_price
from syskatrpxy import calculate_atr
from datetime import datetime, time
from zoneinfo import ZoneInfo

def get_entry_signal(df=None):
    # 1. Fetch Cascade Signals
    entry_l4, exit_l2 = get_signal(df)
    
    # 2. VWAP (ST) Priority & Directional Flow
    st_entry, st_price = get_st_signal(df)
    
    # Current Price for ATM/OTM logic
    last_price = df['Close'].iloc[-1]
    
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_time = now.time()

    # --- MORNING OVERRIDE (9:16–9:30) [KEPT ORIGINAL] ---
    if time(9, 16) <= current_time < time(9, 30):
        if exit_l2 in ["BUY", "BULL"]: return "RISE", exit_l2
        if exit_l2 in ["SELL", "BEAR"]: return "FALL", exit_l2
        return "NONE", exit_l2

    # --- ATR BLOCK ---
    atr_series = calculate_atr(df)
    atr = atr_series.iloc[-1] if not atr_series.empty else 0
    print(f"ATR:{atr:.2f}".center(36))

    # --- FINAL ENTRY MAPPING ---
    final_signal = "NONE"

    # A. BUY LOGIC (Trigger on BEAR or BUY signals)
    # Gated by Bullish VWAP Zone
    if st_entry in ["BUY", "UP", "SIDE"]:
        if entry_l4 in ["BEAR"]:
            # Above VWAP = ATM, Below = OTM
            final_signal = "ATMBUY" if last_price > st_price else "OTMBUY"

    # B. SELL LOGIC (Trigger on BULL or SELL signals)
    # Gated by Bearish VWAP Zone
    if final_signal == "NONE" and st_entry in ["SELL", "DOWN", "SIDE"]:
        if entry_l4 in ["BULL"]:
            # Below VWAP = ATM, Above = OTM
            final_signal = "ATMSELL" if last_price < st_price else "OTMSELL"

    # C. Final Strict Logic Check & Reporting
    if final_signal == "NONE":
        print(f"⛔ 🚧 NO ENTRY 🚧 {entry_l4} 🚧 ⛔".center(36))
    else:
        print(f"🔥 {entry_l4} → {final_signal} (P:{last_price:.2f} vs VWAP:{st_price:.2f})".center(36))
        
    return final_signal, exit_l2



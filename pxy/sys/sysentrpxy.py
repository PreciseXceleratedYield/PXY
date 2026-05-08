# sysentrpxy.py
from sysmktpxy import get_signal
from syscnfgpxy import TICKER
from sysstrndpxy import get_signal as get_st_signal
from syskatrpxy import calculate_atr
from datetime import datetime, time
from zoneinfo import ZoneInfo

def get_entry_signal(df=None):
    # --- CONFIG SWITCH ---
    ALWAYSOTM = True  # Set to False to retain original ATM/OTM logic
    
    # 1. Fetch Basic Signals (L4 Entry, L2 Trend Exit)
    entry_l4, exit_l2 = get_signal(df)
    entry_l4 = exit_l2

    # 2. Fetch ST Signal (IST Anchored White Line Engine)
    st_trend, st_price = get_st_signal(df)

    # Time Management
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_time = now.time()

    # ==========================================
    # 3. ENTRY MAPPING LOGIC (ST SYNCED)
    # ==========================================
    final_signal = "NONE"

    # --- PHASE A: BULLISH MOMENTUM (ST is UP or BUY) ---
    if st_trend in ["BUY", "UP"]:
        if entry_l4 == "BUY":
            final_signal = "ATMBUY"  # Upgrade to ATM in Trend
        elif entry_l4 == "SELL":
            final_signal = "OTMSELL" # Stay OTM for Counter-trend
        else:
            final_signal = entry_l4   # Pass through BULL/BEAR etc.

    # --- PHASE B: BEARISH MOMENTUM (ST is SELL or DOWN) ---
    elif st_trend in ["SELL", "DOWN"]:
        if entry_l4 == "SELL":
            final_signal = "ATMSELL" # Upgrade to ATM in Trend
        elif entry_l4 == "BUY":
            final_signal = "OTMBUY"  # Stay OTM for Counter-trend
        else:
            final_signal = entry_l4   # Pass through BULL/BEAR etc.

    # --- PHASE C: NEUTRAL / SIDE ---
    else:
        final_signal = entry_l4 # Pass through original signal if ST is neutral

    # ==========================================
    # 4. OVERRIDE LOGIC (MORNING & ALWAYSOTM)
    # ==========================================
    
    # Check for Morning Window OR Global Switch
    is_morning = time(9, 15) <= current_time < time(10, 00)
    
    if is_morning or ALWAYSOTM:
        if final_signal == "ATMBUY":
            final_signal = "OTMBUY"
        elif final_signal == "ATMSELL":
            final_signal = "OTMSELL"

    # Reporting
    if final_signal in ["BULL", "BEAR", "NONE"]:
        print(f"⛔ 🚧 NO ENTRY (ST:{st_trend}) 🚧 {final_signal} 🚧 ⛔".center(36))
    else:
        print(f"🔥 {entry_l4} → {final_signal} (ST:{st_trend})".center(36))

    return final_signal, exit_l2

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 36)
        print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")






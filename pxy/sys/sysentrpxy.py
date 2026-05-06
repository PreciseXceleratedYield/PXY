# sysentrpxy.py
from sysmktpxy import get_signal
from syscnfgpxy import TICKER
from sysstrndpxy import get_signal as get_st_signal
from syskatrpxy import calculate_atr
from datetime import datetime, time
from zoneinfo import ZoneInfo

def get_entry_signal(df=None):
    # 1. Fetch Basic Signals (L4 Entry, L2 Trend Exit)
    entry_l4, exit_l2 = get_signal(df)
    
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
            final_signal = "ATMBUY"   # Upgraded to ATM
        elif entry_l4 == "SELL":
            final_signal = "OTMSELL"  # Counter-trend stays OTM
        else:
            final_signal = "NONE"

    # --- PHASE B: BEARISH MOMENTUM (ST is SELL or DOWN) ---
    elif st_trend in ["SELL", "DOWN"]:
        if entry_l4 == "SELL":
            final_signal = "ATMSELL"  # Upgraded to ATM
        elif entry_l4 == "BUY":
            final_signal = "OTMBUY"   # Counter-trend stays OTM
        else:
            final_signal = "NONE"

    # --- PHASE C: NEUTRAL / SIDE ---
    else:
        final_signal = "NONE"

    # ==========================================
    # 4. MORNING OVERRIDE (9:15 to 10:00)
    # ==========================================
    # Force OTM during high morning volatility regardless of ATM upgrade
    if time(9, 15) <= current_time < time(10, 00):
        if final_signal == "ATMBUY":
            final_signal = "OTMBUY"
        elif final_signal == "ATMSELL":
            final_signal = "OTMSELL"

    # Reporting
    if final_signal == "NONE":
        print(f"⛔ 🚧 NO ENTRY (ST:{st_trend}) 🚧 ⛔".center(36))
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





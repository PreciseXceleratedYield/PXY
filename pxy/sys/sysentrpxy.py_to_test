
# sysentrpxy.py
from sysmktpxy import get_signal
from syscnfgpxy import TICKER
from sysstrndpxy import get_signal as get_st_signal
from syskatrpxy import calculate_atr, calculate_dynamic_k
from syshkinpxy import detect_ha_flip_signal
from datetime import datetime, time
from zoneinfo import ZoneInfo

def get_entry_signal(df=None):
    # 1. Fetch Cascade Signals (Confirmed Entry, Trend Exit)
    entry_l4, exit_l2 = get_signal(df)

    # 2. Fetch Values
    atr_series = calculate_atr(df)
    atr = atr_series.iloc[-1] if not (atr_series is None or atr_series.empty) else 0
    k_val = calculate_dynamic_k(df)
    ha_sig, past_d, ce_d, pe_d = detect_ha_flip_signal(df)

    # Time Management
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_time = now.time()

    # --- FINAL ENTRY MAPPING (Unified for Morning & Day) ---
    final_signal = "NONE"

    if entry_l4 == "BULL":
        # SELL on BULL signal if green depth is high (Contrarian)
        if ce_d > (atr / 3):
            final_signal = "ATMSELL"
        else:
            final_signal = "BULL"

    elif entry_l4 == "BEAR":
        # BUY on BEAR signal if red depth is high (Contrarian)
        if pe_d > (atr / 3):
            final_signal = "ATMBUY"
        else:
            final_signal = "BEAR"

    # Standard "BUY" or "SELL" signals are ignored (stay NONE)
    else:
        final_signal = "NONE"

    # Reporting
    if final_signal in ["BULL", "BEAR", "NONE"]:
        print(f"⛔ 🚧 NO ENTRY 🚧 {final_signal} 🚧 ⛔".center(36))
    else:
        print(f"🔥 {entry_l4} → {final_signal}".center(36))

    return final_signal, exit_l2

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 36)
        print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")


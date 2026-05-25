# sysentrpxy.py
from sysmktpxy import get_signal  # <-- Import from Tier 2 Network Layer
from syspowrpxy import get_ce_pe_power  # <-- IMPORTED Tier 3 Power Engine Layer

try:
    from syscnfgpxy import TICKER
except ImportError:
    TICKER = "NSE_INDEX"

def get_entry_signal(df=None):
    # 1. Fetch Raw Signals from Tier 2 Network Layer (BUY, SELL, BULL, BEAR, or NONE)
    entry_signal, exit_signal = get_signal(df)
    if entry_signal:
        entry_signal = entry_signal.upper()

    final_signal = "NONE"

    # 2. Fetch Intraday CE/PE Momentum Power Arrays (Outputs integers 1 to 10)
    direction, ce_power, pe_power = get_ce_pe_power(df)

    # 3. DIRECT PASSTHROUGH & EXCLUSIVE POWER FLOOR TRIGGERING
    if entry_signal == "BUY":
        final_signal = "ATMBUY"
    elif entry_signal == "SELL":
        final_signal = "ATMSELL"
        
    # Condition: BULL and CE Power < 2 (Triggers only when CE Power is exactly 1)
    elif entry_signal == "BULL":
        if ce_power < 2:
            final_signal = "STSELL"
        else:
            final_signal = "BULL"
            
    # Condition: BEAR and PE Power < 2 (Triggers only when PE Power is exactly 1)
    elif entry_signal == "BEAR":
        if pe_power < 2:
            final_signal = "STBUY"
        else:
            final_signal = "BEAR"
    else:
        final_signal = "NONE"

    # 4. ABSOLUTE END CATCH-ALL
    if final_signal == "NONE" and exit_signal:
        final_signal = exit_signal.upper().strip()

    # 5. ACTION LOGGER
    if final_signal in ["ATMBUY", "ATMSELL", "CROSSSELL", "CROSSBUY"]:
        print(f"🔥 ACTION LAYER ROUTER DEPLOYED : {final_signal} (CE:{ce_power} | PE:{pe_power}) 🔥")

    return final_signal, exit_signal




# sysentrpxy.py
from sysmktpxy import get_signal  # <-- Import from Tier 2 Network Layer

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

    # 2. DIRECT PASSTHROUGH TO ATM STRIKE CONVERGENCE
    if entry_signal == "BUY":
        final_signal = "ATMBUY"
    elif entry_signal == "SELL":
        final_signal = "ATMSELL"
    elif entry_signal in ["BULL", "BEAR"]:
        final_signal = entry_signal
    else:
        final_signal = "NONE"

    # 3. ABSOLUTE END CATCH-ALL
    if final_signal == "NONE" and exit_signal:
        final_signal = exit_signal.upper().strip()

    # 4. ACTION LOGGER
    if final_signal in ["ATMBUY", "ATMSELL"]:
        print(f"🔥 ACTION LAYER ROUTER DEPLOYED : {final_signal} 🔥")

    return final_signal, exit_signal




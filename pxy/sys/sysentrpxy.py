from datetime import datetime, time
import math
from pathlib import Path
import sys

import pandas as pd

# Upstream PXY Pipeline Architectures
from sysmktpxy import get_signal as get_market_signal
from sysstrndpxy import get_market_trend as get_supertrend_signal
from syscnfgpxy import (
    SYSCNFGPXY_NEW_BOOK_CUTOFF,
    SYSCNFGPXY_TIMEZONE,
)

EXE_DIR = Path(__file__).resolve().parent / "exe"
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

from execoolpxy import cooldown_remaining


def _apply_new_book_cutoff(entry_signal, exit_signal, now_time):
    """
    Preserves structural exit signals while cleanly dropping active 
    entry signals to 'NONE' if the current session time passes the system cutoff.
    """
    if now_time >= SYSCNFGPXY_NEW_BOOK_CUTOFF:
        entry_signal = "NONE"
    return entry_signal, exit_signal


def get_entry_signal(df=None, *, processed_supertrend=None, now=None):
    """
    Routes entry and exit signals dynamically based on the session timeline:
    - 09:00 AM to 09:30 AM IST: Both Entry and Exit driven by MKT pipeline.
    - After 09:30 AM IST: Entry driven by MKT pipeline, Exit driven by ST pipeline.
    """
    # 1. Enforce strict safety post-square-off structural cooldown locks
    if cooldown_remaining() > 0:
        print("⏳ POST-SQUARE-OFF COOLDOWN: entry and exit signals forced to NONE.")
        return "NONE", "NONE"

    # 2. Resolve internal current time context relative to configured Timezone
    if now is None:
        now_time = datetime.now(SYSCNFGPXY_TIMEZONE).time()
    elif isinstance(now, datetime):
        now_time = now.time()
    else:
        now_time = now

    # 3. Handle upstream data collection fallback structures
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    # 4. Define hard timeline boundary switch matrix parameters
    mkt_start = time(9, 0)
    switch_cutoff = time(9, 30)

    # Fetch live operational frames from both pipelines up front
    raw_mkt = str(get_market_signal(df)).upper().strip()
    mkt_signal = raw_mkt if raw_mkt in {"BULL", "BEAR"} else "NONE"

    if processed_supertrend is not None:
        raw_st = get_supertrend_signal(processed_supertrend)
    else:
        raw_st = get_supertrend_signal(df)
    st_signal = str(raw_st).upper().strip()
    if st_signal not in {"BULL", "BEAR", "SIDE"}:
        st_signal = "NONE"

    # 5. Dynamic Pipeline Switch Matrix Route
    if mkt_start <= now_time <= switch_cutoff:
        # ==============================================================================
        # 🔄 EARLY WINDOW (09:00 AM - 09:30 AM): BOTH ENTRY & EXIT DRIVEN BY MKT
        # ==============================================================================
        if mkt_signal == "BULL":
            entry_sig = "BUY"
            exit_sig = "BULL"
        elif mkt_signal == "BEAR":
            entry_sig = "SELL"
            exit_sig = "BEAR"
        else:
            entry_sig, exit_sig = "NONE", "NONE"
            
        print(f"⏱️ [WINDOW: 09:00-09:30] Entry: MKT({mkt_signal}) | Exit: MKT({mkt_signal})")
    
    else:
        # ==============================================================================
        # 📈 LATER WINDOW (AFTER 09:30 AM): ENTRY DRIVEN BY MKT, EXIT DRIVEN BY ST
        # ==============================================================================
        # Evaluate Entry Pipeline Layer (Stays exclusively anchored to MKT)
        if mkt_signal == "BULL":
            entry_sig = "BUY"
        elif mkt_signal == "BEAR":
            entry_sig = "SELL"
        else:
            entry_sig = "NONE"

        # Evaluate Exit Pipeline Layer (Switches completely over to ST)
        if st_signal == "BULL":
            exit_sig = "BULL"
        elif st_signal == "BEAR":
            exit_sig = "BEAR"
        elif st_signal == "SIDE":
            # Neutralizing exit signal inside consolidating ST market states to protect capital
            exit_sig = "NONE"
            print("⏸️ [ST CONSOLIDATION] Exit pipeline detects SIDEWAYS trend. Forcing flat exit state.")
        else:
            exit_sig = "NONE"
            
        print(f"⏱️ [WINDOW: AFTER 09:30] Entry: MKT({mkt_signal}) | Exit: ST({st_signal})")

    # 6. Apply system end-of-session cutoff rules to the calculated entry signal
    return _apply_new_book_cutoff(entry_sig, exit_sig, now_time)


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    print("--- STARTING LIVE PXY DUAL-PIPE ENTRY SYSTEM ROUTER ---")
    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"RESULT >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")
    else:
        print("CRITICAL Upstream data feed empty.")


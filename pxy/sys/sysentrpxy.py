
from datetime import datetime, time
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
    Preserve structural exit signals while blocking new entries
    at or after the configured system cutoff.
    """
    if now_time >= SYSCNFGPXY_NEW_BOOK_CUTOFF:
        entry_signal = "NONE"

    return entry_signal, exit_signal


def get_entry_signal(df=None, *, processed_supertrend=None, now=None):
    """
    Dynamically route entry and exit signals using the session timeline.

    09:00-09:30 IST:
        Entry = MKT
        Exit  = MKT

    09:30-14:45 IST:
        Entry = MKT
        Exit  = ST

    14:45-15:40 IST:
        Entry = MKT
        Exit  = MKT

    Outside the MKT windows:
        Entry = MKT
        Exit  = ST

    The configured new-book cutoff and post-square-off cooldown
    remain in effect.
    """

    # 1. Enforce post-square-off structural cooldown locks.
    if cooldown_remaining() > 0:
        print(
            "⏳ POST-SQUARE-OFF COOLDOWN: "
            "entry and exit signals forced to NONE."
        )
        return "NONE", "NONE"

    # 2. Resolve current time in the configured timezone.
    if now is None:
        now_time = datetime.now(SYSCNFGPXY_TIMEZONE).time()
    elif isinstance(now, datetime):
        now_time = now.time()
    else:
        now_time = now

    # 3. Handle upstream data collection fallback.
    if df is None:
        from sysdtafpxy import fetch_yf_data

        df = fetch_yf_data()

    # 4. Define pipeline routing windows.
    mkt_start = time(9, 0)
    morning_cutoff = time(9, 30)
    evening_start = time(14, 45)
    evening_cutoff = time(15, 40)

    # 5. Obtain MKT signal.
    raw_mkt = str(get_market_signal(df)).upper().strip()
    mkt_signal = (
        raw_mkt
        if raw_mkt in {"BULL", "BEAR"}
        else "NONE"
    )

    # 6. Obtain Supertrend signal.
    if processed_supertrend is not None:
        raw_st = get_supertrend_signal(processed_supertrend)
    else:
        raw_st = get_supertrend_signal(df)

    st_signal = str(raw_st).upper().strip()

    if st_signal not in {"BULL", "BEAR", "SIDE"}:
        st_signal = "NONE"

    # 7. Select MKT for both entry and exit in the specified windows.
    use_mkt_for_both = (
        mkt_start <= now_time <= morning_cutoff
        or evening_start <= now_time <= evening_cutoff
    )

    if use_mkt_for_both:
        # MKT drives both entry and exit.
        if mkt_signal == "BULL":
            entry_sig = "BUY"
            exit_sig = "BULL"
        elif mkt_signal == "BEAR":
            entry_sig = "SELL"
            exit_sig = "BEAR"
        else:
            entry_sig = "NONE"
            exit_sig = "NONE"

        print(
            f"⏱️ Entry: MKT({mkt_signal}) | "
            f"Exit: MKT({mkt_signal})"
        )

    else:
        # Entry remains exclusively driven by MKT.
        if mkt_signal == "BULL":
            entry_sig = "BUY"
        elif mkt_signal == "BEAR":
            entry_sig = "SELL"
        else:
            entry_sig = "NONE"

        # Exit remains driven by Supertrend.
        if st_signal == "BULL":
            exit_sig = "BULL"
        elif st_signal == "BEAR":
            exit_sig = "BEAR"
        else:
            exit_sig = "NONE"

            if st_signal == "SIDE":
                print(
                    "⏸️ Pipeline detects SIDEWAYS trend."
                )

        print(
            f"⏱️ Entry: MKT({mkt_signal}) | "
            f"Exit: ST({st_signal})"
        )

    # 8. Apply the existing configured new-book cutoff.
    return _apply_new_book_cutoff(
        entry_sig,
        exit_sig,
        now_time,
    )


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    print(
        "--- STARTING LIVE PXY DUAL-PIPE "
        "ENTRY SYSTEM ROUTER ---"
    )

    df = fetch_yf_data()

    if df is not None and not df.empty:
        entry_sig, exit_sig = get_entry_signal(df)

        print(
            f"RESULT >> ENTRY_SIG: {entry_sig} | "
            f"EXIT_SIG: {exit_sig}"
        )
    else:
        print("CRITICAL Upstream data feed empty.")

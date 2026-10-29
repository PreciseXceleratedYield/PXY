from datetime import datetime, time as dt_time
from pathlib import Path
import sys

import pandas as pd

# Upstream PXY Pipeline Architecture
from sysmktpxy import get_signal as get_market_signal
from syscnfgpxy import SYSCNFGPXY_TIMEZONE

EXE_DIR = Path(__file__).resolve().parent / "exe"
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

from execoolpxy import cooldown_remaining


# Fresh-entry window (Asia/Kolkata)
ENTRY_START = dt_time(9, 16)
ENTRY_END = dt_time(13, 16)


def _apply_new_book_cutoff(entry_signal, exit_signal, now_time):
    """
    Permit fresh-entry signals only from 09:16 inclusive
    until 13:16 exclusive.

    This time restriction applies ONLY to entry signals.
    Preserve the existing exit signal.
    """
    if not (ENTRY_START <= now_time < ENTRY_END):
        entry_signal = "NONE"

    return entry_signal, exit_signal


def get_entry_signal(df=None, *, processed_supertrend=None, now=None):
    """
    Route entry and exit signals exclusively through MKT.

    Fresh-entry signals are permitted only from 09:16 to
    13:16 Asia/Kolkata time.

    Outside this window, entry is forced to NONE while
    the MKT-derived exit signal is preserved.

    Post-square-off cooldown behavior remains unchanged.

    processed_supertrend is retained for function signature
    compatibility but is not used.
    """

    # 1. Enforce the existing post-square-off cooldown.
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

    # 3. Fetch market data when not supplied.
    if df is None:
        from sysdtafpxy import fetch_yf_data

        df = fetch_yf_data()

    # 4. Obtain and validate the MKT signal.
    raw_mkt = str(get_market_signal(df)).upper().strip()

    mkt_signal = (
        raw_mkt
        if raw_mkt in {"BULL", "BEAR"}
        else "NONE"
    )

    # 5. MKT exclusively drives both entry and exit.
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

    # 6. Apply the entry-only time restriction.
    return _apply_new_book_cutoff(
        entry_sig,
        exit_sig,
        now_time,
    )


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    print(
        "--- STARTING LIVE PXY MKT-ONLY "
        "ENTRY/EXIT ROUTER ---"
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


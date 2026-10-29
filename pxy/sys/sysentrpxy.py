
from datetime import datetime
from pathlib import Path
import sys

import pandas as pd

# Upstream PXY Pipeline Architecture
from sysmktpxy import get_signal as get_market_signal
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
    Block new entries at or after the configured cutoff.
    Preserve the existing exit signal.
    """
    if now_time >= SYSCNFGPXY_NEW_BOOK_CUTOFF:
        entry_signal = "NONE"

    return entry_signal, exit_signal


def get_entry_signal(df=None, *, processed_supertrend=None, now=None):
    """
    Route both entry and exit signals exclusively through MKT.

    MKT drives entry and exit throughout the trading day.
    The configured new-book cutoff and post-square-off cooldown
    remain in effect.

    processed_supertrend is retained for function signature
    compatibility but is no longer used.
    """

    # 1. Enforce post-square-off cooldown.
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

    # 6. Apply the configured new-book cutoff.
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


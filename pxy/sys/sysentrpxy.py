
from datetime import datetime, time as dt_time
from pathlib import Path
import sys

import pandas as pd

# Existing MKT pipeline remains the source of exit signals.
from sysmktpxy import get_signal as get_market_signal

# New independent GTIN pipeline supplies entry signals only.
from sysgtinpxy import get_entry_signal as get_gtin_entry_signal

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

    This restriction applies ONLY to entry signals.
    The existing exit signal is preserved.
    """
    if not (ENTRY_START <= now_time < ENTRY_END):
        entry_signal = "NONE"

    return entry_signal, exit_signal


def get_entry_signal(df=None, *, processed_supertrend=None, now=None):
    """
    Route entry and exit signals through separate pipelines.

    Entry:
        GTIN running-candle close-to-close signal.

    Exit:
        Existing MKT/DTHA signal, unchanged.

    Fresh entries are permitted only from 09:16 to 13:16
    in the configured timezone.

    Existing cooldown behavior and return signature are preserved.

    processed_supertrend is retained for signature compatibility.
    """

    # 1. Preserve the existing post-square-off cooldown.
    if cooldown_remaining() > 0:
        print(
            "⏳ POST-SQUARE-OFF COOLDOWN: "
            "entry and exit signals forced to NONE."
        )
        return "NONE", "NONE"

    # 2. Resolve the current time in the configured timezone.
    if now is None:
        now_time = datetime.now(SYSCNFGPXY_TIMEZONE).time()
    elif isinstance(now, datetime):
        now_time = now.time()
    else:
        now_time = now

    # 3. Fetch market data once and pass the same frame to both pipelines.
    if df is None:
        from sysdtafpxy import fetch_yf_data

        df = fetch_yf_data()

    # 4. Entry signal: independent GTIN pipeline.
    raw_entry = str(get_gtin_entry_signal(df)).upper().strip()

    entry_sig = (
        raw_entry
        if raw_entry in {"BUY", "SELL"}
        else "NONE"
    )

    # 5. Exit signal: existing MKT pipeline, unchanged.
    raw_mkt = str(get_market_signal(df)).upper().strip()

    mkt_signal = (
        raw_mkt
        if raw_mkt in {"BULL", "BEAR"}
        else "NONE"
    )

    if mkt_signal == "BULL":
        exit_sig = "BULL"
    elif mkt_signal == "BEAR":
        exit_sig = "BEAR"
    else:
        exit_sig = "NONE"

    print(
        f"⏱️ Entry: GTIN({entry_sig}) | "
        f"Exit: MKT({mkt_signal})"
    )

    # 6. Preserve the existing entry-only time restriction.
    return _apply_new_book_cutoff(
        entry_sig,
        exit_sig,
        now_time,
    )


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    print(
        "--- STARTING LIVE PXY GTIN ENTRY / "
        "EXISTING MKT EXIT ROUTER ---"
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

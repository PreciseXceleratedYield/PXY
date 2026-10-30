
from datetime import datetime, time as dt_time
from pathlib import Path
import sys

# Existing MKT pipeline.
from sysmktpxy import get_signal as get_market_signal

# Existing GTIN entry pipeline, retained for MKT mode.
from sysgtinpxy import get_entry_signal as get_gtin_entry_signal

# New RSIG entry + exit pipeline.
from sysrsigpxy import get_signals as get_rsig_signals

from syscnfgpxy import SYSCNFGPXY_TIMEZONE

EXE_DIR = Path(__file__).resolve().parent / "exe"
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

from execoolpxy import cooldown_remaining


# Select the signal pipeline:
# "MKT"  = existing GTIN entry + MKT exit behavior.
# "RSIG" = RSIG entry + RSIG exit behavior.
SIGNAL_MODE = "RSIG"

# Fresh-entry window (Asia/Kolkata).
ENTRY_START = dt_time(9, 16)
ENTRY_END = dt_time(13, 16)


def _apply_new_book_cutoff(entry_signal, exit_signal, now_time):
    """
    Permit fresh-entry signals only from 09:16 inclusive
    until 13:16 exclusive.

    This restriction applies ONLY to entry signals.
    The exit signal is preserved.
    """
    if not (ENTRY_START <= now_time < ENTRY_END):
        entry_signal = "NONE"

    return entry_signal, exit_signal


def get_entry_signal(df=None, *, processed_supertrend=None, now=None):
    """
    Return (entry_signal, exit_signal).

    SIGNAL_MODE:
        MKT:
            Entry = existing GTIN pipeline.
            Exit  = existing MKT pipeline.

        RSIG:
            Entry = RSIG pipeline.
            Exit  = RSIG pipeline.

    Existing cooldown, time-window, function signature,
    and tuple return behavior are preserved.

    processed_supertrend is retained for signature compatibility.
    """

    # 1. Preserve the existing post-square-off cooldown.
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

    # 3. Fetch market data once and share the same frame.
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    # 4. Select the signal pipeline.
    mode = str(SIGNAL_MODE).upper().strip()

    if mode == "MKT":
        # Original behavior: GTIN entry + MKT exit.
        raw_entry = str(get_gtin_entry_signal(df)).upper().strip()
        entry_sig = (
            raw_entry
            if raw_entry in {"BUY", "SELL"}
            else "NONE"
        )

        raw_exit = str(get_market_signal(df)).upper().strip()
        exit_sig = (
            raw_exit
            if raw_exit in {"BULL", "BEAR"}
            else "NONE"
        )

    elif mode == "RSIG":
        # RSIG calculates both signals from the same data snapshot.
        raw_entry, raw_exit = get_rsig_signals(df)

        raw_entry = str(raw_entry).upper().strip()
        raw_exit = str(raw_exit).upper().strip()

        entry_sig = (
            raw_entry
            if raw_entry in {"BUY", "SELL"}
            else "NONE"
        )
        exit_sig = (
            raw_exit
            if raw_exit in {"BULL", "BEAR"}
            else "NONE"
        )

    else:
        # Invalid mode must not create an entry or exit signal.
        print(f"⚠️ INVALID SIGNAL_MODE: {SIGNAL_MODE!r}. Signals forced to NONE.")
        return "NONE", "NONE"

    print(
        f"⏱️ Mode: {mode} | "
        f"Entry: {entry_sig} | "
        f"Exit: {exit_sig}"
    )

    # 5. Preserve the existing entry-only time restriction.
    return _apply_new_book_cutoff(
        entry_sig,
        exit_sig,
        now_time,
    )


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    print(f"--- STARTING PXY {SIGNAL_MODE} ENTRY / EXIT ROUTER ---")

    df = fetch_yf_data()

    if df is not None and not df.empty:
        entry_sig, exit_sig = get_entry_signal(df)
        print(
            f"RESULT >> ENTRY_SIG: {entry_sig} | "
            f"EXIT_SIG: {exit_sig}"
        )
    else:
        print("CRITICAL Upstream data feed empty.")


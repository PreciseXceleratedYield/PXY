from datetime import datetime
from pathlib import Path
import sys

from sysmktpxy import get_signals as get_market_signals
from syscnfgpxy import (
    SYSCNFGPXY_TIMEZONE,
    SYSCNFGPXY_MARKET_OPEN,
    SYSCNFGPXY_ENTRY_CUTOFF,
)

EXE_DIR = Path(__file__).resolve().parent / "exe"
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

from execoolpxy import cooldown_remaining, liquidation_pending


ENTRY_START = SYSCNFGPXY_MARKET_OPEN
ENTRY_END = SYSCNFGPXY_ENTRY_CUTOFF


def _apply_new_book_cutoff(entry_signal, exit_signal, now_time):
    """Apply the existing entry-only market-hours restriction."""
    if not (ENTRY_START <= now_time < ENTRY_END):
        entry_signal = "NONE"
    return entry_signal, exit_signal


def get_entry_signal(df=None, *, processed_supertrend=None, now=None):
    """Return the unchanged (entry_signal, exit_signal) tuple contract."""
    if liquidation_pending():
        print("🛑 MASTER RISK LIQUIDATION PENDING: new entries are blocked.")
        return "NONE", "NONE"

    if cooldown_remaining() > 0:
        print(
            "⏳ POST-SQUARE-OFF COOLDOWN: "
            "entry and exit signals forced to NONE."
        )
        return "NONE", "NONE"

    if now is None:
        now_time = datetime.now(SYSCNFGPXY_TIMEZONE).time()
    elif isinstance(now, datetime):
        now_time = now.time()
    else:
        now_time = now

    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    raw_entry, raw_exit = get_market_signals(df)
    raw_entry = str(raw_entry).upper().strip()
    raw_exit = str(raw_exit).upper().strip()

    entry_sig = raw_entry if raw_entry in {"BUY", "SELL"} else "NONE"
    exit_sig = raw_exit if raw_exit in {"BULL", "BEAR", "SIDE"} else "NONE"

    print(f"⏱️ IN: {entry_sig} | OUT: {exit_sig}")
    return _apply_new_book_cutoff(entry_sig, exit_sig, now_time)


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"RESULT >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")
    else:
        print("CRITICAL Upstream data feed empty.")

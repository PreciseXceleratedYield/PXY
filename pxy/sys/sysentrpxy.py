from datetime import datetime
from pathlib import Path
import sys

from sysmktpxy import get_signal as get_market_signal
from syscnfgpxy import SYSCNFGPXY_NEW_BOOK_CUTOFF, SYSCNFGPXY_TIMEZONE

EXE_DIR = Path(__file__).resolve().parent / "exe"
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

from execoolpxy import cooldown_remaining


def _entry_signal_for_exit(exit_signal, now=None):
    """Return a new-book entry unless the IST cutoff has passed."""
    normalized_exit = str(exit_signal).upper().strip()
    if normalized_exit not in {"BULL", "BEAR"}:
        return "NONE", "NONE"
    if now is None:
        now = datetime.now(SYSCNFGPXY_TIMEZONE).time()
    entry_signal = (
        {"BULL": "BUY", "BEAR": "SELL"}.get(normalized_exit, "NONE")
        if now < SYSCNFGPXY_NEW_BOOK_CUTOFF
        else "NONE"
    )
    return entry_signal, normalized_exit


def get_entry_signal(df=None):
    """Map the canonical MKT exit direction to a binary BUY/SELL entry."""
    if cooldown_remaining() > 0:
        print("⏳ POST-SQUARE-OFF COOLDOWN: entry and exit signals forced to NONE.")
        return "NONE", "NONE"

    exit_signal = str(get_market_signal(df)).upper().strip()
    if exit_signal not in {"BULL", "BEAR"}:
        exit_signal = "NONE"
    return _entry_signal_for_exit(exit_signal)


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")

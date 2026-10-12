from pathlib import Path
import sys

from sysmktpxy import get_signal as get_market_signal

EXE_DIR = Path(__file__).resolve().parent / "exe"
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

from execoolpxy import cooldown_remaining


def get_entry_signal(df=None):
    """Map the canonical MKT exit direction to a binary BUY/SELL entry."""
    if cooldown_remaining() > 0:
        print("⏳ POST-SQUARE-OFF COOLDOWN: entry and exit signals forced to NONE.")
        return "NONE", "NONE"

    exit_signal = str(get_market_signal(df)).upper().strip()
    if exit_signal not in {"BULL", "BEAR"}:
        exit_signal = "NONE"
    entry_signal = {"BULL": "BUY", "BEAR": "SELL"}.get(exit_signal, "NONE")
    return entry_signal, exit_signal


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")

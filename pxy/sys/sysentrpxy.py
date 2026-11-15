from datetime import datetime
from pathlib import Path
import sys

from sysmrngpxy import get_morning_direction
from syscnfgpxy import (
    SYSCNFGPXY_TIMEZONE,
    SYSCNFGPXY_FRESH_ENTRY_START,
    SYSCNFGPXY_FRESH_ENTRY_END,
)

EXE_DIR = Path(__file__).resolve().parent / "exe"
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

from execoolpxy import cooldown_remaining, liquidation_pending


ENTRY_START = SYSCNFGPXY_FRESH_ENTRY_START
ENTRY_END = SYSCNFGPXY_FRESH_ENTRY_END


def _apply_new_cycle_cutoff(entry_signal, exit_signal, now_time):
    """Apply the existing entry-only market-hours restriction."""
    if not (ENTRY_START <= now_time < ENTRY_END):
        entry_signal = {"BUY": "BNON", "SELL": "SNON"}.get(entry_signal, entry_signal)
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

    # All-session OC2 authority: same raw DTAF running-candle comparison as morning.
    # No SUPR, SDIR, SMA qualification, raw cross-check, or BOS priority.
    try:
        _, direction = get_morning_direction()
        direction = str(direction).upper().strip()
        entry_sig = {"UP": "BUY", "DOWN": "SELL"}.get(direction, "NONE")
        exit_sig = {"UP": "BULL", "DOWN": "BEAR"}.get(direction, "NONE")
    except Exception as exc:
        print(f"⚠️ OC2 direction unavailable: {exc}")
        entry_sig, exit_sig = "NONE", "NONE"
    print(f"⏱️ OC2 | IN: {entry_sig} | OUT: {exit_sig}")
    return _apply_new_cycle_cutoff(entry_sig, exit_sig, now_time)

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"RESULT >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")
    else:
        print("CRITICAL Upstream data feed empty.")

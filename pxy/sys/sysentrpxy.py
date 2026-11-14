from datetime import datetime, time as dt_time
from pathlib import Path
import sys

from sysmktpxy import get_signals as get_market_signals
from sysdirpxy import detect_raw_direction
from sysmrngpxy import get_morning_direction
from sysbbospxy import get_bos_bar
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
MORNING_OVERRIDE_END = dt_time(9, 30)


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

    # Morning direction override uses MRNG's PIPE transformation of raw DTAF candles, independent of DTHA.
    # Master liquidation, cooldown, and entry-time restrictions still take precedence.
    if ENTRY_START <= now_time < MORNING_OVERRIDE_END:
        try:
            _, direction = get_morning_direction()
            direction = str(direction).upper().strip()
            entry_sig = {"UP": "BUY", "DOWN": "SELL"}.get(direction, "NONE")
            exit_sig = {"UP": "BULL", "DOWN": "BEAR"}.get(direction, "NONE")
        except Exception as exc:
            print(f"⚠️ Morning direction override unavailable: {exc}")
            entry_sig, exit_sig = "NONE", "NONE"
        # BOS has entry priority from market activation, including the morning window.
        # Morning OC2 remains the sole OUT authority until 09:30.
        try:
            from sysdtafpxy import fetch_yf_data
            bos_df = df if df is not None else fetch_yf_data()
            _, bos_signal = get_bos_bar(bos_df)
            bos_signal = str(bos_signal).upper().strip()
            if bos_signal in {"NBUY", "MBUY"}:
                entry_sig = "BUY"
            elif bos_signal in {"NSELL", "MSELL"}:
                entry_sig = "SELL"
        except Exception as exc:
            print(f"⚠️ Morning BOS entry priority unavailable: {exc}")
        print(f"⏱️ MORNING OVERRIDE | IN: {entry_sig} | OUT: {exit_sig}")
        return _apply_new_cycle_cutoff(entry_sig, exit_sig, now_time)

    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    raw_entry, raw_exit = get_market_signals(df)
    raw_entry = str(raw_entry).upper().strip()
    raw_exit = str(raw_exit).upper().strip()

    # Additional IN trigger: opposite raw direction versus current OUT state.
    # Leave OUT unchanged.
    if raw_exit in {"BULL", "BEAR"}:
        try:
            _, raw_direction = detect_raw_direction(df)
            raw_direction = str(raw_direction).upper().strip()
            if raw_exit == "BULL" and raw_direction == "DOWN":
                raw_entry = "BUY"
            elif raw_exit == "BEAR" and raw_direction == "UP":
                raw_entry = "SELL"
        except Exception as exc:
            print(f"⚠️ IN direction cross-check unavailable: {exc}")

    # Breakout signals take priority over existing IN signals after 09:30.
    # BOS labels remain MBUY/MSELL until its configured morning end (10:10),
    # so include those labels to avoid a 09:30-10:10 priority gap.
    # OUT and all risk/time gates remain unchanged.
    if now_time >= MORNING_OVERRIDE_END:
        try:
            _, bos_signal = get_bos_bar(df)
            bos_signal = str(bos_signal).upper().strip()
            if bos_signal in {"NBUY", "MBUY"}:
                raw_entry = "BUY"
            elif bos_signal in {"NSELL", "MSELL"}:
                raw_entry = "SELL"
        except Exception as exc:
            print(f"⚠️ Breakout entry priority unavailable: {exc}")

    entry_sig = raw_entry if raw_entry in {"BUY", "SELL"} else "NONE"
    exit_sig = raw_exit if raw_exit in {"BULL", "BEAR", "SIDE"} else "NONE"

    print(f"⏱️ IN: {entry_sig} | OUT: {exit_sig}")
    return _apply_new_cycle_cutoff(entry_sig, exit_sig, now_time)


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"RESULT >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")
    else:
        print("CRITICAL Upstream data feed empty.")

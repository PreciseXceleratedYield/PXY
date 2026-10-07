from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
from syscnfgpxy import (
    SYSCNFGPXY_TIMEZONE,
    SYSENTRPXY_DIRECTION_ONLY_END,
    SYSENTRPXY_DIRECTION_ONLY_START,
)
from sysmktpxy import get_signal as get_market_signal
from sysexitpxy import detect_raw_direction
from sysstrndpxy import calculate_supertrend

EXE_DIR = Path(__file__).resolve().parent / "exe"
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

from execoolpxy import cooldown_remaining


def get_entry_signal(df=None, current_time=None):
    """Return entry and exit signals using the morning direction-only window.

    From 09:00 until 09:30 IST, both signals follow market direction. Afterwards,
    entry follows Supertrend and a SIDE Supertrend exit falls back to direction.
    """
    if cooldown_remaining() > 0:
        print("⏳ POST-SQUARE-OFF COOLDOWN: entry and exit signals forced to NONE.")
        return "NONE", "NONE"

    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    if current_time is None:
        current_time = datetime.now(SYSCNFGPXY_TIMEZONE).time()
    elif isinstance(current_time, datetime):
        if current_time.tzinfo is not None:
            current_time = current_time.astimezone(SYSCNFGPXY_TIMEZONE)
        current_time = current_time.time()
    elif getattr(current_time, "tzinfo", None) is not None:
        current_time = current_time.replace(tzinfo=None)

    if SYSENTRPXY_DIRECTION_ONLY_START <= current_time < SYSENTRPXY_DIRECTION_ONLY_END:
        _, market_direction = detect_raw_direction(df)
        market_direction = str(market_direction).upper().strip()
        if market_direction == "UP":
            return "BUY", "BULL"
        if market_direction == "DOWN":
            return "SELL", "BEAR"
        return "NONE", "NONE"

    try:
        processed_st_df = calculate_supertrend(df.copy())
        if processed_st_df is None or processed_st_df.empty:
            trend = "NONE"
        else:
            trend = str(processed_st_df["ST_Trend"].iloc[-1]).upper().strip()
    except Exception as e:
        print(f"⚠️ Trend engine failed ({e}); signals forced to NONE.")
        return "NONE", "NONE"

    if trend == "BULL":
        return "BUY", "BULL"
    if trend == "BEAR":
        return "SELL", "BEAR"
    if trend == "SIDE":
        _, market_signal = get_market_signal(df)
        market_signal = str(market_signal).upper().strip()
        if market_signal == "BULL":
            return "SIDE", "BULL"
        if market_signal == "BEAR":
            return "SIDE", "BEAR"
        return "SIDE", "NONE"
    return "NONE", "NONE"


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")

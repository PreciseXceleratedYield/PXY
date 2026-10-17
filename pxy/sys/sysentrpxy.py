from datetime import datetime
import math
from pathlib import Path
import sys

import pandas as pd

from sysmktpxy import get_signal as get_market_signal
from syscnfgpxy import (
    SYSENTRPXY_VARIANT,
    SYSCNFGPXY_NEW_BOOK_CUTOFF,
    SYSCNFGPXY_TIMEZONE,
)
from sysdtstpxy import calculate_supertrend

EXE_DIR = Path(__file__).resolve().parent / "exe"
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

from execoolpxy import cooldown_remaining


def _entry_signal_for_exit(exit_signal, now=None):
    """Return a new-book entry unless the IST cutoff has passed."""
    normalized_exit = str(exit_signal).upper().strip()
    if normalized_exit not in {"BULL", "BEAR"}:
        return "NONE", "NONE"
    entry_signal = {"BULL": "BUY", "BEAR": "SELL"}[normalized_exit]
    return _apply_new_book_cutoff(entry_signal, normalized_exit, now)


def _apply_new_book_cutoff(entry_signal, exit_signal, now=None):
    """Preserve the exit signal while blocking new entries after the cutoff."""
    if now is None:
        now = datetime.now(SYSCNFGPXY_TIMEZONE).time()
    if now >= SYSCNFGPXY_NEW_BOOK_CUTOFF:
        entry_signal = "NONE"
    return entry_signal, exit_signal


def _finite_row_values(row, columns):
    try:
        values = tuple(
            float(pd.to_numeric(row[name], errors="coerce"))
            for name in columns
        )
    except (TypeError, ValueError, OverflowError):
        return None
    return values if all(math.isfinite(value) for value in values) else None


def _supertrend_entry_signal(
    df, market_exit_signal, now=None, processed_supertrend=None
):
    """Use Supertrend for entries and preserve the independent MKT exit signal."""
    if df is None or df.empty:
        return "NONE", market_exit_signal

    if processed_supertrend is None:
        try:
            processed = calculate_supertrend(df.copy())
        except Exception as error:
            print(f"⚠️ Trend engine failed ({error}); STS entry forced to NONE.")
            return "NONE", market_exit_signal
    else:
        processed = processed_supertrend
    if processed is None or processed.empty or "ST_Trend" not in processed:
        return "NONE", market_exit_signal

    trend = str(processed["ST_Trend"].iloc[-1]).upper().strip()
    if trend not in {"BULL", "BEAR"}:
        return _apply_new_book_cutoff("NONE", market_exit_signal, now)

    latest = processed.iloc[-1]
    entry_signal = "NONE"

    # Entry requires trend direction and a close within half an ATR of the ST line.
    if {"Close", "st_line", "st_atr"}.issubset(processed.columns):
        values = _finite_row_values(latest, ("Close", "st_line", "st_atr"))
        if values is not None:
            price, st_line, atr = values
            if atr > 0:
                entry_atr = atr / 2.0
                if trend == "BULL" and st_line <= price <= st_line + entry_atr:
                    entry_signal = "BUY"
                elif trend == "BEAR" and st_line - entry_atr <= price <= st_line:
                    entry_signal = "SELL"
    return _apply_new_book_cutoff(entry_signal, market_exit_signal, now)


def get_entry_signal(df=None, *, processed_supertrend=None, now=None):
    """Route entries through MKT or STS while always sourcing exits from MKT."""
    if cooldown_remaining() > 0:
        print("⏳ POST-SQUARE-OFF COOLDOWN: entry and exit signals forced to NONE.")
        return "NONE", "NONE"

    if now is None:
        now = datetime.now(SYSCNFGPXY_TIMEZONE).time()
    if df is None:
        from sysdtafpxy import fetch_yf_data

        df = fetch_yf_data()

    market_signal = str(get_market_signal(df)).upper().strip()
    if market_signal not in {"BULL", "BEAR"}:
        market_signal = "NONE"

    if SYSENTRPXY_VARIANT == "STS":
        return _supertrend_entry_signal(
            df,
            market_signal,
            now=now,
            processed_supertrend=processed_supertrend,
        )
    return _entry_signal_for_exit(market_signal, now=now)


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")

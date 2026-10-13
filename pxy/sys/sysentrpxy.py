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
    SYSSTRNDPXY_ST1_FACTOR,
)
from sysstrndpxy import calculate_supertrend

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


def _supertrend_entry_signal(df, now=None):
    """Apply the historical ST/MKT countertrend pullback entry rules."""
    if df is None or df.empty:
        return "NONE", "NONE"

    try:
        processed = calculate_supertrend(df.copy())
    except Exception as error:
        print(f"⚠️ Trend engine failed ({error}); signals forced to NONE.")
        return "NONE", "NONE"
    if processed is None or processed.empty or "ST_Trend" not in processed:
        return "NONE", "NONE"

    trend = str(processed["ST_Trend"].iloc[-1]).upper().strip()
    if trend not in {"BULL", "BEAR", "SIDE"}:
        return "NONE", "NONE"

    market_signal = str(get_market_signal(df)).upper().strip()
    if market_signal not in {"BULL", "BEAR"}:
        market_signal = "NONE"

    latest = processed.iloc[-1]
    entry_signal = "NONE"
    if trend in {"BULL", "BEAR"}:
        if {"Close", "st_line", "st_atr"}.issubset(processed.columns):
            values = _finite_row_values(latest, ("Close", "st_line", "st_atr"))
            if values is not None and values[2] > 0:
                price, st_line, atr = values
                zone_width = (SYSSTRNDPXY_ST1_FACTOR / 2.0) * atr
                if (
                    trend == "BULL"
                    and market_signal == "BEAR"
                    and st_line <= price <= st_line + zone_width
                ):
                    entry_signal = "BUY"
                elif (
                    trend == "BEAR"
                    and market_signal == "BULL"
                    and st_line - zone_width <= price <= st_line
                ):
                    entry_signal = "SELL"
        return _apply_new_book_cutoff(entry_signal, trend, now)

    if {"Close", "st_line", "st_mirror"}.issubset(processed.columns):
        values = _finite_row_values(latest, ("Close", "st_line", "st_mirror"))
        if values is not None:
            price, st_line, mirror = values
            upper_band, lower_band = max(st_line, mirror), min(st_line, mirror)
            band_width = upper_band - lower_band
            if band_width > 0:
                lower_quarter = lower_band + band_width * 0.25
                upper_quarter = upper_band - band_width * 0.25
                if price <= lower_quarter and market_signal == "BEAR":
                    entry_signal = "BUY"
                elif price >= upper_quarter and market_signal == "BULL":
                    entry_signal = "SELL"
    exit_signal = market_signal if market_signal in {"BULL", "BEAR"} else "NONE"
    return _apply_new_book_cutoff(entry_signal, exit_signal, now)


def get_entry_signal(df=None):
    """Route entries through the configured MKT or Supertrend variant."""
    if cooldown_remaining() > 0:
        print("⏳ POST-SQUARE-OFF COOLDOWN: entry and exit signals forced to NONE.")
        return "NONE", "NONE"

    if SYSENTRPXY_VARIANT == "ST":
        if df is None:
            from sysdtafpxy import fetch_yf_data

            df = fetch_yf_data()
        return _supertrend_entry_signal(df)

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

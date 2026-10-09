from pathlib import Path
import math
import sys

import pandas as pd
from sysmktpxy import get_signal as get_market_signal
from sysstrndpxy import calculate_supertrend

EXE_DIR = Path(__file__).resolve().parent / "exe"
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

from execoolpxy import cooldown_remaining

def get_entry_signal(df=None):
    """Filter countertrend entries by MKT direction and Supertrend ATR zones."""
    if cooldown_remaining() > 0:
        print("⏳ POST-SQUARE-OFF COOLDOWN: entry and exit signals forced to NONE.")
        return "NONE", "NONE"

    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    if df is None or df.empty:
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

    trend = str(trend).upper().strip()
    market_signal = (
        str(get_market_signal(df)).upper().strip()
        if trend in {"BULL", "BEAR", "SIDE"}
        else "NONE"
    )

    if trend == "BULL":
        entry_signal = _countertrend_entry(
            processed_st_df,
            market_signal,
            expected_market="BEAR",
            signal="BUY",
            trend="BULL",
        )
        return entry_signal, "BULL"
    if trend == "BEAR":
        entry_signal = _countertrend_entry(
            processed_st_df,
            market_signal,
            expected_market="BULL",
            signal="SELL",
            trend="BEAR",
        )
        return entry_signal, "BEAR"
    if trend == "SIDE":
        entry_signal = "NONE"
        required_columns = {"Close", "st_line", "st_mirror"}
        if required_columns.issubset(processed_st_df.columns):
            latest = processed_st_df.iloc[-1]
            first_band = pd.to_numeric(latest["st_line"], errors="coerce")
            second_band = pd.to_numeric(latest["st_mirror"], errors="coerce")
            price = pd.to_numeric(latest["Close"], errors="coerce")
            if all(math.isfinite(value) for value in (first_band, second_band, price)):
                upper_band = max(first_band, second_band)
                lower_band = min(first_band, second_band)
                band_width = upper_band - lower_band
                if band_width > 0:
                    lower_quarter_limit = lower_band + band_width * 0.25
                    upper_quarter_limit = upper_band - band_width * 0.25
                    if price <= lower_quarter_limit and market_signal == "BEAR":
                        entry_signal = "BUY"
                    elif price >= upper_quarter_limit and market_signal == "BULL":
                        entry_signal = "SELL"
        exit_signal = market_signal if market_signal in {"BULL", "BEAR"} else "NONE"
        return entry_signal, exit_signal
    return "NONE", "NONE"


def _countertrend_entry(
    processed_st_df,
    market_signal: str,
    *,
    expected_market: str,
    signal: str,
    trend: str,
) -> str:
    if market_signal != expected_market:
        return "NONE"
    required_columns = {"Close", "st_line", "st_atr"}
    if not required_columns.issubset(processed_st_df.columns):
        return "NONE"

    latest = processed_st_df.iloc[-1]
    price = pd.to_numeric(latest["Close"], errors="coerce")
    st_line = pd.to_numeric(latest["st_line"], errors="coerce")
    atr = pd.to_numeric(latest["st_atr"], errors="coerce")
    if not all(math.isfinite(value) for value in (price, st_line, atr)) or atr <= 0:
        return "NONE"

    zone_width = 1.5 * atr
    if trend == "BULL" and st_line <= price <= st_line + zone_width:
        return signal
    if trend == "BEAR" and st_line - zone_width <= price <= st_line:
        return signal
    return "NONE"


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")

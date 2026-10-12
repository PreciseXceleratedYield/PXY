from pathlib import Path
import sys

from sysmktpxy import get_signal as get_market_signal
from sysstrndpxy import calculate_supertrend

EXE_DIR = Path(__file__).resolve().parent / "exe"
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

from execoolpxy import cooldown_remaining


def get_entry_signal(df=None):
    """Return entry BUY/SELL mapped directly from the current exit direction."""
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
    except Exception as error:
        print(f"⚠️ Trend engine failed ({error}); signals forced to NONE.")
        return "NONE", "NONE"

    if trend == "BULL":
        exit_signal = "BULL"
    elif trend == "BEAR":
        exit_signal = "BEAR"
    elif trend == "SIDE":
        market_signal = str(get_market_signal(df)).upper().strip()
        exit_signal = market_signal if market_signal in {"BULL", "BEAR"} else "NONE"
    else:
        exit_signal = "NONE"

    entry_signal = {"BULL": "BUY", "BEAR": "SELL"}.get(exit_signal, "NONE")
    return entry_signal, exit_signal


if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data

    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry_sig, exit_sig = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry_sig} | EXIT_SIG: {exit_sig}")

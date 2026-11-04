# sysmktpxy.py
from syscnfgpxy import SYSMKTPXY_DEBUG_ENABLED, SYSMKTPXY_ENTRY_FILTER
from sysdthapxy import get_signal_depth_analysis
from sysdtafpxy import fetch_yf_data
from sysinpxy import get_entry_signal
from sysoutpxy import get_signal as get_exit_signal
from syssmapxy import get_sma_signal
from syssdirpxy import get_structure_direction


def get_pxy_data(df):
    """Return the previous (C1) and latest running (C0) raw closes."""
    if df is None or len(df) < 2 or "Close" not in df.columns:
        return None, None
    raw_close = df["Close"]
    return float(raw_close.iloc[-2]), float(raw_close.iloc[-1])


def _print_console_bar(c1, c0, execution_state):
    """Render the live market monitor within its existing fixed-width layout."""
    RST = "\033[0m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YLW = "\033[1;93m"
    GRAY = "\033[90m"

    min_val = min(c1, c0) - 2
    max_val = max(c1, c0) + 2
    scale_width = 10

    def get_clean_bar(val):
        pos = int(((val - min_val) / (max_val - min_val)) * scale_width) if max_val != min_val else 1
        pos = max(1, pos)
        return ("█" * pos).ljust(scale_width)

    candle_color = GRN if c0 > c1 else RED if c0 < c1 else YLW
    rows = [
        (c1, f"PREV C1:{int(c1):<5}", candle_color),
        (c0, f"RUN  C0:{int(c0):<5}", candle_color),
    ]
    rows.sort(key=lambda item: item[0], reverse=True)

    indicator = "🟢" if execution_state == "BULL" else "🔴" if execution_state == "BEAR" else "⚪"
    print(f"\n{YLW}====== PXY MONITOR LIVE ENGINE  {indicator}  ======={RST}")
    for val, label, color in rows:
        print(f"     {color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val)}{GRAY}]{RST}")
    print(f"{YLW}=========================================={RST}")


def get_signals(df=None):
    """Route IN's execution action and OUT's BULL/BEAR/SIDE state without extra filters."""
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", "NONE"
    try:
        entry_signal = str(get_entry_signal(df)).upper().strip()
        exit_signal = str(get_exit_signal(df)).upper().strip()
        if entry_signal not in {"BUY", "SELL"}:
            entry_signal = "NONE"
        if exit_signal not in {"BULL", "BEAR", "SIDE"}:
            exit_signal = "NONE"

        # Apply the configured entry filter consistently, without a 10:00 time switch.
        if entry_signal in {"BUY", "SELL"}:
            if SYSMKTPXY_ENTRY_FILTER == "SMA":
                try:
                    filter_direction = get_sma_signal(df)["status"]
                except Exception:
                    filter_direction = "NA"
            elif SYSMKTPXY_ENTRY_FILTER == "SDIR":
                filter_direction = get_structure_direction(df).get("direction")
            else:
                filter_direction = None

            if filter_direction is not None and (
                (entry_signal == "BUY" and filter_direction != "BULL")
                or (entry_signal == "SELL" and filter_direction != "BEAR")
            ):
                entry_signal = "NONE"

        if SYSMKTPXY_DEBUG_ENABLED:
            analysis = get_signal_depth_analysis(df)
            if analysis["previous_close"] is not None and analysis["current_close"] is not None:
                _print_console_bar(
                    analysis["previous_close"],
                    analysis["current_close"],
                    exit_signal,
                )
        return entry_signal, exit_signal
    except Exception as exc:
        if SYSMKTPXY_DEBUG_ENABLED:
            print(f"Engine Err: {str(exc)[:25]:<25}")
        return "NONE", "NONE"


def get_signal(df=None):
    """Compatibility wrapper: return the OUT channel's directional signal."""
    return get_signals(df)[1]


if __name__ == "__main__":
    entry, exit_ = get_signals()
    print(f"IN >> ENTRY: {entry} | OUT >> EXIT: {exit_}")

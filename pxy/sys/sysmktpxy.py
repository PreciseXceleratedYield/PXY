# sysmktpxy.py
from syscnfgpxy import SYSMKTPXY_DEBUG_ENABLED
from sysdthapxy import get_signal_depth_analysis
from sysdtafpxy import fetch_yf_data

def get_pxy_data(df):
    """
    Return the previous and current closes from the supplied candle frame.
    """
    df = df.copy()
    raw_close = df['Close'].values
    c0 = float(raw_close[-1])
    c1 = float(raw_close[-2]) if len(raw_close) > 1 else c0
    return c1, c0

def _print_console_bar(c1, c0, execution_state):
    """Renders the display profiling within a strict 42-char layout block."""
    RST = "\033[0m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YLW = "\033[1;93m"
    GRAY = "\033[90m"

    min_val = min(c1, c0) - 2
    max_val = max(c1, c0) + 2
    # Reduced scale width down to 10 to guarantee total length fits inside 42 chars
    scale_width = 10

    def get_clean_bar(val):
        pos = int(((val - min_val) / (max_val - min_val)) * scale_width) if max_val != min_val else 1
        pos = max(1, pos)
        return ("█" * pos).ljust(scale_width)

    candle_color = GRN if c0 >= c1 else RED

    # Formatted to perfectly alignment within bounds
    rows = [
        (c1, f"PREV C1:{int(c1):<5}", candle_color),
        (c0, f"RUN  C0:{int(c0):<5}", candle_color)
    ]
    rows.sort(key=lambda item: item[0], reverse=True)

    # Dynamic indicator assignment for the header string replacement
    if execution_state == "BULL":
        indicator = "🟢"
    elif execution_state == "BEAR":
        indicator = "🔴"
    else:
        indicator = "⚪"

    # All text boundaries and lines are measured to exactly 42 characters wide
    print(f"\n{YLW}====== PXY MONITOR LIVE ENGINE  {indicator}  ======={RST}")
    for val, label, color in rows:
        print(f"     {color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val)}{GRAY}]{RST}")
    print(f"{YLW}=========================================={RST}")
    #print(f" DIR : {YLW}{execution_state:<34}{RST}")

def get_signal(df=None):
    """
    Classify three-close reversals and directional continuations.

    V reversals return BUY/BULL or SELL/BEAR. Three strictly rising or falling
    closes return BUY/BULL or SELL/BEAR, respectively.
    """
    if df is None:
        df = fetch_yf_data()
        
    try:
        analysis = get_signal_depth_analysis(df)
        signal = analysis["signal"]
        signals = {
            "BUY": ("BUY", "BULL"),
            "SELL": ("SELL", "BEAR"),
            "BULL": ("BUY", "BULL"),
            "BEAR": ("SELL", "BEAR"),
        }.get(signal, ("NONE", "NONE"))
        execution_state = signals[1]

        if SYSMKTPXY_DEBUG_ENABLED and analysis["previous_close"] is not None:
            c1 = analysis["previous_close"]
            c0 = analysis["current_close"]
            _print_console_bar(c1, c0, execution_state)
            
        return signals

    except Exception as e:
        if SYSMKTPXY_DEBUG_ENABLED:
            # Error string capped cleanly to avoid terminal distortion wrapping
            err_msg = str(e)[:25]
            print(f"Engine Err: {err_msg:<25}")
        return "NONE", "NONE"

if __name__ == "__main__":
    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry, ex = get_signal(df)
        # Production output script signals formatted layout block
        print(f"OUT >> ENTRY: {entry:<4} | EXIT: {ex:<4}")

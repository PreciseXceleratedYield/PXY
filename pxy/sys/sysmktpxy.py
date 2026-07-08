# pxy_engine.py
from sysdthapxy import fetch_yf_data 

DEBUG = True

def _print_console_bar(c1, o1, c0, o0, execution_state):
    """Renders the graphical console display profiling the active live running candle."""
    RST = "\033[0m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YLW = "\033[1;93m"
    GRAY = "\033[90m"

    min_val = min(c1, c0, o1, o0) - 2
    max_val = max(c1, c0, o1, o0) + 2
    scale_width = 20

    def get_clean_bar(val, marker="█"):
        pos = int(((val - min_val) / (max_val - min_val)) * scale_width) if max_val != min_val else 1
        pos = max(1, pos)
        return (marker * pos).ljust(scale_width)

    c1_color = GRN if c1 >= o1 else RED
    c0_color = GRN if c0 >= o0 else RED

    rows = [
        (c1, f"CLOSED C1-{c1:.2f}", "█", c1_color),
        (c0, f"ACTIVE C0-{c0:.2f}", "█", c0_color)
    ]
    rows.sort(key=lambda item: item, reverse=True)

    print(f"\n{YLW}=== GEOMETRIC ENGINE CONSOLE MONITOR (LIVE) ==={RST}")
    for val, label, marker, color in rows:
        print(f"{color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val, marker)}{GRAY}]{RST}")
    print(f"{YLW}========================================{RST}")
    print(f"       ACTIVE RUNNING CANDLE STATE: {YLW}{execution_state}{RST}")

def get_signal(df=None):
    """
    Evaluates the live running candle against the previous closed candle using strict boundaries.
    Returns: (entry_signal, exit_signal) -> ("BULL", "BULL"), ("BEAR", "BEAR"), or ("NONE", "NONE")
    """
    if df is None:
        df = fetch_yf_data()
        
    if df is None or len(df) < 2:
        return "NONE", "NONE"

    try:
        # Extract previous closed candle (C1) and active live candle (C0)
        c1 = float(df.iloc[-2]['Close'])
        c0 = float(df.iloc[-1]['Close'])

        # =====================================================================
        # 🛡️ EXCLUSIVE CONDITIONAL COMPARE MATRIX (NO SYSTEM DEFAULTS)
        # =====================================================================
        if c0 > c1:
            execution_state = "BULL"
            
        elif c0 < c1:
            execution_state = "BEAR"
            
        else:
            # Explicit lockout: Absolute physical flat line with no movement
            execution_state = "NONE"
        # =====================================================================

        # Render geometric profile layout 
        if DEBUG:
            _print_console_bar(float(df.iloc[-2]['Close']), float(df.iloc[-2]['Open']), 
                               float(df.iloc[-1]['Close']), float(df.iloc[-1]['Open']), 
                               execution_state)
            
        # Split twin signals directly to downstream pipelines
        return execution_state, execution_state

    except Exception as e:
        if DEBUG:
            print(f"Signal Processing Engine Exception: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry, ex = get_signal(df)
        print(f"SPLIT OUTPUT SIGNALS >> ENTRY: {entry} | EXIT: {ex}")


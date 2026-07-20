# pxy_signals.py
import pandas as pd
import numpy as np
import time
from sysdtafpxy import fetch_yf_data

# Import your data engine module cleanly
import pxy_engine

DEBUG = True

def _print_console_bar(prev_c, curr_c, execution_state, pxy_color):
    """Renders the visual monitor mapping current running close against previous close baseline."""
    RST = "\033[0m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YLW = "\033[1;93m"
    GRAY = "\033[90m"

    min_val = min(prev_c, curr_c) - 2
    max_val = max(prev_c, curr_c) + 2
    scale_width = 20

    def get_clean_bar(val):
        pos = int(((val - min_val) / (max_val - min_val)) * scale_width) if max_val != min_val else 1
        pos = max(1, pos)
        return ("█" * pos).ljust(scale_width)

    # Pick console brush directly from the data engine's color assignment
    candle_color = GRN if pxy_color == "green" else RED

    rows = [
        (curr_c, f"RUNNING HA_CLOSE  C0-{round(curr_c, 2)}", candle_color),
        (prev_c, f"PREVIOUS HA_CLOSE C1-{round(prev_c, 2)}", GRAY)
    ]
    rows.sort(key=lambda item: item[0], reverse=True)

    print(f"\n{YLW}=MOMENTUM ENGINE MONITOR: HA CLOSE VS PREV CLOSE={RST}")
    for val, label, color in rows:
        print(f"{color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val)}{GRAY}]{RST}")
    print(f"{YLW}======================================================={RST}")
    print(f"       LIVE MOMENTUM DIRECTION : {candle_color}{execution_state}{RST}")


def get_signal(df=None, live_tick=None):
    """
    Evaluates market direction comparing current running HA close to previous HA close.
    Returns: (entry_signal, exit_signal) -> ("BULL", "BULL"), ("BEAR", "BEAR"), or ("NONE", "NONE")
    """
    if df is None:
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    try:
        # Cross-module call straight into your mathematical data framework
        _, _, pxy_color_series, final_df = pxy_engine.get_pxy_data(df=df, live_tick=live_tick)
        
        if len(final_df) < 2:
            return "NONE", "NONE"

        # MOMENTUM MATRIX: Extract current unclosed close vs last completely closed close
        prev_ha_close = float(final_df['Close'].iloc[-2]) 
        curr_ha_close = float(final_df['Close'].iloc[-1]) 
        running_color = pxy_color_series.iloc[-1]          

        # =====================================================================
        # 🛡️ MOMENTUM COMPLIANT SIGNALS MATRIX
        # =====================================================================
        if running_color == "green" and curr_ha_close > prev_ha_close:
            execution_state = "BULL"
        elif running_color == "red" and curr_ha_close < prev_ha_close:
            execution_state = "BEAR"
        else:
            execution_state = "NONE"
        # =====================================================================

        # Render layout tracking the baseline comparison
        if DEBUG:
            _print_console_bar(prev_ha_close, curr_ha_close, execution_state, running_color)
            
        return execution_state, execution_state

    except Exception as e:
        if DEBUG:
            print(f"Signal Processing Engine Exception: {e}")
        return "NONE", "NONE"


def run_live_pipeline():
    """Simulates your complete live stream ticker environment inside terminal."""
    print("Connecting to live streaming engine...")
    historical_df = fetch_yf_data()
    
    if historical_df is not None and not historical_df.empty:
        base_open = historical_df['Open'].iloc[-1]
        base_high = historical_df['High'].iloc[-1]
        base_low = historical_df['Low'].iloc[-1]
        running_price = historical_df['Close'].iloc[-1]
        
        print("Streaming live ticks now. Press Ctrl+C to terminate.")
        try:
            for tick in range(1, 6):
                # Fluctuate the price live up and down
                running_price += np.random.uniform(-1.0, 1.0)
                base_high = max(base_high, running_price)
                base_low = min(base_low, running_price)
                
                live_packet = {
                    'Open': base_open,
                    'High': base_high,
                    'Low': base_low,
                    'Close': running_price
                }
                
                entry, ex = get_signal(historical_df, live_tick=live_packet)
                print(f"🔄 Tick {tick} | Spot raw price: {round(running_price, 2)} | Momentum Signal: {entry}")
                time.sleep(1.5)
                
        except KeyboardInterrupt:
            print("\nStream halted cleanly.")

if __name__ == "__main__":
    # Execute loop instantly on launch
    run_live_pipeline()



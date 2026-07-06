import numpy as np
import pandas as pd
from sysmktpxy import get_signal  # Original direction engine fallback (UP / DOWN)

def get_entry_signal(df=None, length: int = 21, upper_mult: float = 1.4, lower_mult: float = 1.4):
    """
    Advanced routing pipeline driven exclusively by Linear Regression Channel states.
    Priority 1: Upper/Lower wick touches (Current & Past) override everything.
    Priority 2 (Entry Fallback): Uses the original sysmktpxy get_signal tool.
    Priority 2 (Exit Fallback): Always follows the structural channel direction.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
    if df is None or df.empty or len(df) < length:
        return "NONE", "NONE"

    # =========================================================================
    # LINEAR REGRESSION CHANNEL MATH ENGINE (For Exits and Touch Checks)
    # =========================================================================
    source_vals = df['Close'].iloc[-length:].values
    x = np.arange(length)
    y = source_vals
    
    slope, intercept = np.polyfit(x, y, 1)
    start_price = intercept                  
    end_price = intercept + slope * (length - 1)  

    # Structural Channel Trend Direction for Exits
    channel_trend = "BULL" if end_price > start_price else "BEAR"

    # Replicate standard deviation calculations for channel boundaries
    average = np.mean(source_vals)
    periods = length - 1
    
    std_dev_acc = 0.0
    for j in range(length):
        val = start_price + slope * j
        price_diff = source_vals[j] - val
        std_dev_acc += price_diff * price_diff

    divisor = 1.0 if periods == 0 else float(periods)
    std_dev = np.sqrt(std_dev_acc / divisor)

    # Reconstruct live upper and lower boundary lines
    val_track = start_price + slope * np.arange(length)
    linreg_upper = val_track[-1] + (upper_mult * std_dev)
    linreg_lower = val_track[-1] - (lower_mult * std_dev)

    # Slice current (t) and past closed (t-1) candles
    current_high, prev_high = df['High'].iloc[-1], df['High'].iloc[-2]
    current_low, prev_low = df['Low'].iloc[-1], df['Low'].iloc[-2]

    # Check for wick touches (current or past candle)
    high_touches_upper = (current_high >= linreg_upper) or (prev_high >= linreg_upper)
    low_touches_lower = (current_low <= linreg_lower) or (prev_low <= linreg_lower)

    # =========================================================================
    # PRIORITY EXECUTION MATRIX (Touch overrides all | Fallback to sysmktpxy)
    # =========================================================================
    if high_touches_upper:
        entry_signal = "ATMSELL"
        exit_signal = "BEAR"
        log_state = "TOUCH_UPPER_SELL"
    elif low_touches_lower:
        entry_signal = "ATMBUY"
        exit_signal = "BULL"
        log_state = "TOUCH_LOWER_BUY"
    else:
        # ENTRY FALLBACK: Call your original engine to get "UP" or "DOWN"
        direction, _ = get_signal(df)
        entry_signal = "ATMBUY" if direction == "UP" else "ATMSELL"
        
        # EXIT FALLBACK: Always strictly follows the structural channel slope direction
        exit_signal = channel_trend
        log_state = f"FALLBACK_ENGINE_{direction}"

    # =========================================================================
    # SYSTEM OUTPUT TERMINAL LOGS
    # =========================================================================
    print(f" ROUTE LOG: {log_state}")
    print(f" ENTRY: {entry_signal} | EXIT: {exit_signal}")
        
    return entry_signal, exit_signal

import numpy as np
import pandas as pd
from sysmktpxy import get_signal  # Fallback engine (UP / DOWN)

def get_entry_signal(df=None, length: int = 21, upper_mult: float = 1.4, lower_mult: float = 1.4):
    """
    Advanced routing pipeline driven by Linear Regression Channel states.
    Priority 1 (TOP): Channel trend direction change (BULL->BEAR = Actionable ATMSELL | BEAR->BULL = Actionable ATMBUY).
    Priority 2 (MID): Candle wick touches against boundary bands (Actionable ATMBUY or ATMSELL).
    Priority 3 (LOW): Fallback engine mapped STRICTLY to non-actionable BULL or BEAR strings.
    Exit Signal: Unconditionally locked to the active structural channel direction (BULL / BEAR).
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
    if df is None or df.empty or len(df) < (length + 1):
        return "NONE", "NONE"

    # =========================================================================
    # LINEAR REGRESSION CHANNEL MATH ENGINE
    # =========================================================================
    # --- Current Bar (t) Channel Trend Calculation ---
    source_vals_curr = df['Close'].iloc[-length:].values
    x_arr = np.arange(length)
    slope_curr, intercept_curr = np.polyfit(x_arr, source_vals_curr, 1)
    end_price_curr = intercept_curr + slope_curr * (length - 1)
    
    channel_trend_curr = "BULL" if end_price_curr > intercept_curr else "BEAR"

    # --- Previous Bar (t-1) Channel Trend Calculation ---
    source_vals_prev = df['Close'].iloc[-(length + 1):-1].values
    slope_prev, intercept_prev = np.polyfit(x_arr, source_vals_prev, 1)
    end_price_prev = intercept_prev + slope_prev * (length - 1)
    
    channel_trend_prev = "BULL" if end_price_prev > intercept_prev else "BEAR"

    # --- Compute Requisite Standard Deviation Band Boundaries (Current Bar) ---
    average = np.mean(source_vals_curr)
    periods = length - 1
    std_dev_acc = 0.0
    for j in range(length):
        val = intercept_curr + slope_curr * j
        price_diff = source_vals_curr[j] - val
        std_dev_acc += price_diff * price_diff

    divisor = 1.0 if periods == 0 else float(periods)
    std_dev = np.sqrt(std_dev_acc / divisor)

    # Reconstruct precise active boundary lines
    linreg_upper = (intercept_curr + slope_curr * (length - 1)) + (upper_mult * std_dev)
    linreg_lower = (intercept_curr + slope_curr * (length - 1)) - (lower_mult * std_dev)

    # Slice high/low fields for current (t) and past closed (t-1) candle tracking
    current_high, prev_high = df['High'].iloc[-1], df['High'].iloc[-2]
    current_low, prev_low = df['Low'].iloc[-1], df['Low'].iloc[-2]

    # Evaluate rolling boundary touches
    high_touches_upper = (current_high >= linreg_upper) or (prev_high >= linreg_upper)
    low_touches_lower = (current_low <= linreg_lower) or (prev_low <= linreg_lower)

    # =========================================================================
    # 3-TIER EXCLUSIVE ROUTING MATRIX
    # =========================================================================
    entry_signal = "NONE"
    
    # --- PRIORITY 1: Channel Direction Transitions (Actionable Flipped Signal) ---
    if channel_trend_prev == "BULL" and channel_trend_curr == "BEAR":
        entry_signal = "ATMSELL"
    elif channel_trend_prev == "BEAR" and channel_trend_curr == "BULL":
        entry_signal = "ATMBUY"

    # --- PRIORITY 2: Live/Past Boundary Band Wick Touches (Actionable Touch Signal) ---
    elif high_touches_upper or low_touches_lower:
        if high_touches_upper:
            entry_signal = "ATMSELL"
        else:
            entry_signal = "ATMBUY"

    # --- PRIORITY 3: Fallback Engine Framework (Non-Actionable baseline text) ---
    else:
        direction, _ = get_signal(df)
        
        # Maps engine strictly to raw, non-actionable string labels
        if direction == "UP":
            entry_signal = "BULL"
        else:
            entry_signal = "BEAR"

    # Exit engine unconditionally maps to live structural slope trend
    exit_signal = channel_trend_curr

    # =========================================================================
    # SYSTEM OUTPUT TERMINAL LOGS
    # =========================================================================
    print(f" ENTRY: {entry_signal} | EXIT: {exit_signal}")
        
    return entry_signal, exit_signal



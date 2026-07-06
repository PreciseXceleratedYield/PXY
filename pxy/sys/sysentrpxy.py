import numpy as np
import pandas as pd
from sysmktpxy import get_signal  # Direction engine fallback (UP / DOWN)

def get_entry_signal(df=None, length: int = 21, upper_mult: float = 1.4, lower_mult: float = 1.4):
    """
    Advanced routing pipeline driven by Linear Regression Channel states.
    Priority 1 (TOP): Raw channel transition states (BUY / SELL from closed shifts).
    Priority 2 (MID): Live or past candle wick touches against boundary bands.
    Priority 3 (FALLBACK): Original sysmktpxy engine (UP -> BULL / DOWN -> BEAR).
    Exit: Always tracks the structural linear regression channel slope trend.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
    if df is None or df.empty or len(df) < length:
        return "NONE", "NONE"

    # =========================================================================
    # LINEAR REGRESSION CHANNEL MATH ENGINE
    # =========================================================================
    source_vals = df['Close'].iloc[-length:].values
    x = np.arange(length)
    y = source_vals
    
    slope, intercept = np.polyfit(x, y, 1)
    start_price = intercept                  
    end_price = intercept + slope * (length - 1)  

    # Structural Channel Trend Direction for Exits (Always BULL or BEAR)
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

    # Slice current (t) and past closed (t-1) candles for touch/shift analysis
    current_high, prev_high = df['High'].iloc[-1], df['High'].iloc[-2]
    current_low, prev_low = df['Low'].iloc[-1], df['Low'].iloc[-2]
    current_close, prev_close = df['Close'].iloc[-1], df['Close'].iloc[-2]

    # Replicate rolling window checks for boundary violations
    high_touches_upper = (current_high >= linreg_upper) or (prev_high >= linreg_upper)
    low_touches_lower = (current_low <= linreg_lower) or (prev_low <= linreg_lower)

    # Calculate candle shift states to feed Priority 1 
    prev_close_shift = df['Close'].shift(1).iloc[-1]
    candle_comparison = "BULL" if current_close > prev_close_shift else "BEAR"

    # =========================================================================
    # 3-TIER PRIORITY EXECUTION MATRIX
    # =========================================================================
    
    # --- PRIORITY 1: Raw Channel Transitions (BUY / SELL from shift context) ---
    if high_touches_upper and (not low_touches_lower):
        entry_signal = "ATMSELL"
        exit_signal = channel_trend
        log_state = "SELL"
        
    elif low_touches_lower and (not high_touches_upper):
        entry_signal = "ATMBUY"
        exit_signal = channel_trend
        log_state = "BUY"
        
    # --- PRIORITY 2: Live/Past Wick Touches (Handles concurrent edge cases) ---
    elif high_touches_upper:
        entry_signal = "ATMSELL"
        exit_signal = channel_trend
        log_state = "SELL"
        
    elif low_touches_lower:
        entry_signal = "ATMBUY"
        exit_signal = channel_trend
        log_state = "BUY"
        
    # --- PRIORITY 3: Fallback Framework from sysmktpxy (UP->BULL / DOWN->BEAR) ---
    else:
        direction, _ = get_signal(df)
        fallback_direction = "BULL" if direction == "UP" else "BEAR"
        
        entry_signal = "ATMBUY" if fallback_direction == "BULL" else "ATMSELL"
        exit_signal = channel_trend
        log_state = fallback_direction

    # =========================================================================
    # SYSTEM OUTPUT TERMINAL LOGS
    # =========================================================================
    print(f" MOVE: {log_state}")
    print(f" ENTRY: {entry_signal} | EXIT: {exit_signal}")
        
    return entry_signal, exit_signal



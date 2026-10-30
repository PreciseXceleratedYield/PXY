# ==================================================
# sysstrhpxy.py (STREAMLINED CORE PROXIMITY ENGINE)
# ==================================================
import pandas as pd
import numpy as np

def get_candle_strength_line(df):
    """
    Evaluates pattern rules using clean upstream OC/2 signals.
    Dynamically maps upstream naming variances to prevent KeyError or conversion crashes.
    Returns:
        str: "BUY", "SELL", or "NEUTRAL"
    """
    # Safety Check: Guarantee a minimum baseline history profile size
    if df is None or len(df) < 20:
        return "NEUTRAL"
        
    df = df.copy()
    
    # --------------------------------------------------
    # CRASH PROTECTION: DYNAMIC UPSTREAM COLUMN MAPPING
    # --------------------------------------------------
    # If the exact columns 'is_green' or 'is_red' are missing, detect variations automatically
    if 'is_green' not in df.columns:
        # Check for alternative naming conventions (like 'green', 'Green', 'bar_green', etc.)
        green_col = [c for c in df.columns if 'green' in str(c).lower()]
        if green_col:
            df['is_green'] = df[green_col[0]]
        else:
            # Fallback if entirely missing: use standard Open/Close relationship
            df['is_green'] = df['Close'] > df['Open']

    if 'is_red' not in df.columns:
        red_col = [c for c in df.columns if 'red' in str(c).lower()]
        if red_col:
            df['is_red'] = df[red_col[0]]
        else:
            df['is_red'] = df['Close'] < df['Open']

    # Standardize contents: Convert 1/0, strings ('green'/'red'), or floats into strict True/False
    df['is_green'] = df['is_green'].astype(str).str.lower().isin(['true', '1', '1.0', 'green', 'yes'])
    df['is_red']   = df['is_red'].astype(str).str.lower().isin(['true', '1', '1.0', 'red', 'yes'])

    # --------------------------------------------------
    # PATTERN ENGINE PROCESSING
    # --------------------------------------------------
    last_idx = df.index[-1]
    is_live_green = bool(df.at[last_idx, 'is_green'])
    is_live_red   = bool(df.at[last_idx, 'is_red'])

    # PRIORITY 1: STRICT 7-BAR LOOKBACK (NO MISSES)
    past_7_bars_red = df['is_red'].iloc[-8:-1].all()
    past_7_bars_grn = df['is_green'].iloc[-8:-1].all()
    
    strict_buy  = is_live_green and past_7_bars_red
    strict_sell = is_live_red and past_7_bars_grn
    
    if strict_buy:
        return "BUY"
    if strict_sell:
        return "SELL"

    # IMMEDIATE PAST 3 CONSECUTIVE VERIFICATION
    immediate_3_red = df['is_red'].iloc[-4:-1].all()
    immediate_3_grn = df['is_green'].iloc[-4:-1].all()

    # PRIORITY 2: ROLLBACK SEARCH (1-CANCEL-1-DEMAND)
    target_count = 8
    red_total, green_total = 0, 0
    red_misses, green_misses = 0, 0
    
    rollback_buy_history  = np.zeros(len(df), dtype=bool)
    rollback_sell_history = np.zeros(len(df), dtype=bool)

    for i in range(len(df)):
        is_g = bool(df['is_green'].iloc[i])
        is_r = bool(df['is_red'].iloc[i])
        
        # --- BULLISH RED STREAK PROCESSING ---
        if is_r:
            if red_total == 0:
                red_total = 1
                red_misses = 0
            elif red_misses == 1:
                red_total += 1
                red_misses = 0
            else:
                red_total += 1
        elif is_g:
            if red_total >= 3:
                if red_total >= target_count:
                    rollback_buy_history[i] = True
                    red_total, red_misses = 0, 0
                else:
                    red_misses += 1
                    if red_misses > 1:
                        red_total, red_misses = 0, 0
            else:
                red_total, red_misses = 0, 0
                
        if is_g and red_total >= target_count:
            rollback_buy_history[i] = True
            red_total, red_misses = 0, 0

        # --- BEARISH GREEN STREAK PROCESSING ---
        if is_g:
            if green_total == 0:
                green_total = 1
                green_misses = 0
            elif green_misses == 1:
                green_total += 1
                green_misses = 0
            else:
                green_total += 1
        elif is_r:
            if green_total >= 3:
                if green_total >= target_count:
                    rollback_sell_history[i] = True
                    green_total, green_misses = 0, 0
                else:
                    green_misses += 1
                    if green_misses > 1:
                        green_total, green_misses = 0, 0
            else:
                green_total, green_misses = 0, 0
                
        if is_r and green_total >= target_count:
            rollback_sell_history[i] = True
            green_total, green_misses = 0, 0

    # EVALUATE 14-CANDLE ROLLING WINDOW FLAGS
    rollback_buy_in_window  = any(rollback_buy_history[-14:])
    rollback_sell_in_window = any(rollback_sell_history[-14:])

    valid_rollback_buy  = is_live_green and immediate_3_red and rollback_buy_in_window
    valid_rollback_sell = is_live_red and immediate_3_grn and rollback_sell_in_window

    if valid_rollback_buy:
        return "BUY"
    elif valid_rollback_sell:
        return "SELL"
    
    return "NEUTRAL"




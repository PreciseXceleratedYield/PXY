# ==================================================
# sysstrhpxy.py (FINAL: STREAMLINED SIGNAL RETURN)
# ==================================================
import pandas as pd
from colorama import Fore, Style, init
from sysdthapxy import get_ha_data
from syskatrpxy import calculate_atr
from syssadxpxy import calculate_adx

init(autoreset=True)
TOTAL_WIDTH = 42

def get_candle_strength_line(df=None):
    """
    Evaluates market structure and filters via 1-Cancel-1-Demand criteria.
    Returns:
        str: Only the final signal status ("⚡ BUY", "⚡ SELL", or "Neutral")
    """
    # ------------------------------
    # GET HA DATA (SINGLE CALL ONLY)
    # ------------------------------
    ha_close, ha_open, ha_color, df = get_ha_data(df=df)
    
    # ------------------------------
    # SAFETY CHECK
    # ------------------------------
    if df is None or len(df) == 0:
        return "Neutral"
        
    # ------------------------------
    # STATE MACHINE: STREAK & MISS TRACKING
    # ------------------------------
    target_count = 6
    min_count = 4  # Threshold required before interruption recovery allows
    
    red_total = 0
    green_total = 0
    red_misses = 0
    green_misses = 0
    
    bull_flip = False
    bear_flip = False
    
    # Process historical bars chronologically
    for i in range(len(ha_color)):
        current_color = ha_color.iloc[i]
        is_green = (current_color == "green")
        is_red = (current_color == "red")
        
        # Reset triggers inside loop to isolate the final candle step precisely
        bull_flip = False
        bear_flip = False
        
        # --- BULLISH (RED) STREAK TRACKING ---
        if is_red:
            if red_total == 0:
                red_total = 1
                red_misses = 0
            elif red_misses == 1 and red_total >= min_count:
                red_total += 1
                red_misses = 0
            elif red_misses == 1 and red_total < min_count:
                red_total = 1
                red_misses = 0
            else:
                red_total += 1
        elif is_green:
            if red_total > 0:
                if red_total >= target_count:
                    bull_flip = True
                    red_total = 0
                    red_misses = 0
                elif red_total >= min_count:
                    red_misses += 1
                    if red_misses > 1:
                        red_total = 0
                        red_misses = 0
                else:
                    red_total = 0
                    red_misses = 0

        if is_green and red_total >= target_count:
            bull_flip = True
            red_total = 0
            red_misses = 0

        # --- BEARISH (GREEN) STREAK TRACKING ---
        if is_green:
            if green_total == 0:
                green_total = 1
                green_misses = 0
            elif green_misses == 1 and green_total >= min_count:
                green_total += 1
                green_misses = 0
            elif green_misses == 1 and green_total < min_count:
                green_total = 1
                green_misses = 0
            else:
                green_total += 1
        elif is_red:
            if green_total > 0:
                if green_total >= target_count:
                    bear_flip = True
                    green_total = 0
                    green_misses = 0
                elif green_total >= min_count:
                    green_misses += 1
                    if green_misses > 1:
                        green_total = 0
                        green_misses = 0
                else:
                    green_total = 0
                    green_misses = 0
                    
        if is_red and green_total >= target_count:
            bear_flip = True
            green_total = 0
            green_misses = 0

    # ------------------------------
    # ASSIGN AND RETURN ONLY SIGNAL
    # ------------------------------
    if bull_flip:
        final_signal = "BUY"
    elif bear_flip:
        final_signal = "SELL"
    else:
        final_signal = "Neutral"

    return final_signal

# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    signal = get_candle_strength_line()
    print(f"Output Signal: {signal}")


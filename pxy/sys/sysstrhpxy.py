# ==================================================
# sysstrhpxy.py (FINAL: SAFE + STREAK LOGIC FIXED)
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
    Returns:
    - formatted line
    - strength label
    - score value
    """
    # ------------------------------
    # GET HA DATA (SINGLE CALL ONLY)
    # ------------------------------
    ha_close, ha_open, ha_color, df = get_ha_data(df=df)
    
    # ------------------------------
    # SAFETY CHECK
    # ------------------------------
    if df is None or len(df) == 0:
        strength_label = "CE Weak"
        score_value = 0.0
        strength = "Weak"
        color = Fore.YELLOW
    else:
        # ------------------------------
        # STATE MACHINE: STREAK & MISS TRACKING
        # ------------------------------
        target_count = 6
        min_count = 4  # Minimum threshold required before interruption recovery is allowed
        
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
            
            # Reset triggers inside loop to catch the final state correctly
            bull_flip = False
            bear_flip = False
            
            # --- BULLISH (RED) STREAK TRACKING ---
            if is_red:
                if red_total == 0:
                    red_total = 1
                    red_misses = 0
                elif red_misses == 1 and red_total >= min_count:
                    # 1-to-1 Demand met: Only valid because we met the min 4 requirement before the miss
                    red_total += 1
                    red_misses = 0
                elif red_misses == 1 and red_total < min_count:
                    # Interruption happened before hitting 4: Rule invalid, restart fresh
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
                        # We have at least 4 bars! Activate 1-Cancel protection loop
                        red_misses += 1
                        if red_misses > 1:
                            red_total = 0
                            red_misses = 0
                    else:
                        # Interruption happened below 4 bars: Hard Reset
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
        # TRANSLATE STATES TO OUTPUTS
        # ------------------------------
        if bull_flip:
            strength_label = "⚡ BUY"
            strength = "Strong"
            color = Fore.GREEN
        elif bear_flip:
            strength_label = "⚡ SELL"
            strength = "Strong"
            color = Fore.RED
        else:
            # Neutral / Build-up States
            last_color = ha_color.iloc[-1]
            if last_color == "green":
                strength_label = f"CE Build:{green_total}" if green_total > 0 else "CE Idle"
            else:
                strength_label = f"PE Build:{red_total}" if red_total > 0 else "PE Idle"
            strength = "Weak"
            color = Fore.YELLOW

        # ------------------------------
        # ATR + ADX UNPACKING
        # ------------------------------
        atr_series = calculate_atr(df)
        atr = atr_series.iloc[-1] if not pd.isna(atr_series.iloc[-1]) else 0.0
        
        # Safe extraction of ADX (extracts value if returned as tuple/series/dataframe)
        adx_raw = calculate_adx(df)
        adx_value = 0.0
        
        if adx_raw is not None:
            if isinstance(adx_raw, tuple):
                adx_value = adx_raw[0] # Take first element from tuple
            elif isinstance(adx_raw, (pd.Series, pd.DataFrame)):
                adx_value = adx_raw.iloc[-1] if not adx_raw.empty else 0.0
            else:
                adx_value = float(adx_raw)
                
        # If extracted ADX is still inside a Series array element
        if isinstance(adx_value, pd.Series):
            adx_value = adx_value.iloc[-1] if not adx_value.empty else 0.0

        candle_range = df['High'].iloc[-1] - df['Low'].iloc[-1]

        # ------------------------------
        # SAFE SCORE CALCULATION
        # ------------------------------
        if adx_value is None or pd.isna(adx_value) or atr == 0 or pd.isna(atr):
            score_value = 0.0
        else:
            score_value = (candle_range / atr) * (float(adx_value) / 100)

    # ------------------------------
    # FORMAT OUTPUT
    # ------------------------------
    left_text = f"{color}{strength_label}{Style.RESET_ALL}"
    right_text = f"{color}Score:{score_value:.2f}{Style.RESET_ALL}"
    
    plain_left = strength_label
    plain_right = f"Score:{score_value:.2f}"
    
    space_width = TOTAL_WIDTH - len(plain_left) - len(plain_right)
    if space_width < 0:
        space_width = 1
        
    spacing = " " * space_width
    line = left_text + spacing + right_text
    
    return line, strength, score_value

# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    line, strength, score = get_candle_strength_line()
    print(line)


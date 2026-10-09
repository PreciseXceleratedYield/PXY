# sysdptpxy.py
import pandas as pd
from colorama import init
from sysdthapxy import get_pxy_data
from syscnfgpxy import SYSDPTPXY_LAST_N

init(autoreset=True)

def detect_pxy_flip_signal(df=None, last_n=SYSDPTPXY_LAST_N):
    """Detects signal depth boundaries using the true outputs processed by Script 1."""
    if last_n <= 0:
        return "NA", 1, 1, 1

    output = get_pxy_data(df=df)
    
    if output is None or output[3].empty:
        return "NA", 1, 1, 1
        
    # Read the frozen matrix series out of Script 1
    _, _, pxy_color_series, final_df = output

    if len(final_df) < 5:
        return "NA", 1, 1, 1

    # Safe conversion to python list array formats for lookback scanning
    colors = pxy_color_series.tolist()

    if len(colors) < 2:
        return "NA", 1, 1, 1

    # ==================================================
    # ⚡ PRODUCTION DEPTH ANALYSIS STREAKS
    # ==================================================
    current_color = colors[-1]
    
    # Current Streak Depth Tracking
    current_depth = 0
    for c in reversed(colors):
        if c == current_color:
            current_depth += 1
        else:
            break
    current_depth = max(current_depth, 1)

    # Historical Prior Streak Depth Tracking
    current_streak_start = len(colors) - current_depth
    prev_color = colors[current_streak_start - 1] if current_streak_start > 0 else "none"
    
    past_depth_val = 0
    if current_streak_start > 0:
        prior_scan_start = max(0, current_streak_start - last_n)
        for i in reversed(range(prior_scan_start, current_streak_start)):
            if colors[i] == prev_color:
                past_depth_val += 1
            else:
                break
    past_depth_val = max(past_depth_val, 1)

    # ==================================================
    # 🔥 CORE SIGNAL ROUTER PROCESSOR
    # ==================================================
    if prev_color == "red" and current_color == "green":
        signal = "BUY" if current_depth == 1 else "NA"
    elif prev_color == "green" and current_color == "red":
        signal = "SELL" if current_depth == 1 else "NA"
    elif prev_color == "green" and current_color == "green":
        signal = "BULL" if past_depth_val >= 2 else "NA"
    elif prev_color == "red" and current_color == "red":
        signal = "BEAR" if past_depth_val >= 2 else "NA"
    else:
        signal = "NA"

    # ==================================================
    # 🎯 DERIVED MATRIX OPTION DEPTH BOUNDARIES
    # ==================================================
    ce_depth = current_depth if current_color == "green" else 1
    pe_depth = current_depth if current_color == "red" else 1
    past_depth_str = f"CE{past_depth_val}" if prev_color == "green" else f"PE{past_depth_val}" if prev_color == "red" else "NA"

    return signal, past_depth_str, ce_depth, pe_depth

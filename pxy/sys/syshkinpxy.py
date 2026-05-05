# sysp_depth_pxy.py
import pandas as pd
from colorama import Fore, Style, init

init(autoreset=True)

def get_p_series(df):
    """Calculates the P (Master Price) for the entire dataframe."""
    # e1=C, e2=(C+C1)/2, e3=(C+O)/2, e4=(O+H+L+C)/4
    c = df['Close']
    o = df['Open']
    h = df['High']
    l = df['Low']
    c1 = df['Close'].shift(1)
    
    e1 = c
    e2 = (c1 + c) / 2
    e3 = (c + o) / 2
    e4 = (o + h + l + c) / 4
    
    p_series = (e1 + e2 + e3 + e4) / 4
    return p_series.round(4)

def detect_p_depth_signal(df, last_n=21):
    """
    Detects depth and signals using Master Price (P) instead of HA.
    Green = P increased | Red = P decreased
    """
    if df is None or len(df) < 5:
        return "NA", 1, 1, 1

    # 1. Calculate P-based colors
    p_vals = get_p_series(df)
    
    # Generate colors based on P direction
    # colors[i] is color of candle i compared to i-1
    colors = []
    for i in range(1, len(p_vals)):
        if p_vals.iloc[i] > p_vals.iloc[i-1]:
            colors.append("green")
        elif p_vals.iloc[i] < p_vals.iloc[i-1]:
            colors.append("red")
        else:
            # If flat, maintain previous color to avoid breaking streaks
            colors.append(colors[-1] if colors else "none")

    if len(colors) < 2:
        return "NA", 1, 1, 1

    # 2. Slice for Last N
    colors_n = colors[-last_n:]
    current_color = colors_n[-1]
    
    # 3. CURRENT DEPTH (Streak of current color)
    current_depth = 0
    for c in reversed(colors_n):
        if c == current_color:
            current_depth += 1
        else:
            break
    current_depth = max(current_depth, 1)

    # 4. PAST DEPTH (Streak of previous color)
    current_streak_start = len(colors) - current_depth
    prev_color = colors[current_streak_start - 1] if current_streak_start > 0 else "none"
    
    past_depth_val = 0
    if current_streak_start > 0:
        for i in reversed(range(current_streak_start)):
            if colors[i] == prev_color:
                past_depth_val += 1
            else:
                break
    past_depth_val = max(past_depth_val, 1)

    # 5. SIGNAL LOGIC
    # Flip = Depth 1 | Continuation = Past Depth >= 2
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

    # 6. CE / PE DEPTH
    ce_depth = current_depth if current_color == "green" else 1
    pe_depth = current_depth if current_color == "red" else 1

    # Format past depth label
    past_depth_str = f"CE{past_depth_val}" if prev_color == "green" else f"PE{past_depth_val}" if prev_color == "red" else "NA"

    return signal, past_depth_str, ce_depth, pe_depth

# ---------------- SELF TEST ----------------
if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df_test = fetch_yf_data()
    sig, p_depth, ce_d, pe_d = detect_p_depth_signal(df_test)
    
    print(f"P-Master Signal: {sig}")
    print(f"P-Past Depth: {p_depth}")
    print(f"CE/PE Depth: {ce_d} / {pe_d}")


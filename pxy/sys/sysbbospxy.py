# sysbbospxy.py
from colorama import Fore, Style, init
import pandas as pd
import numpy as np

init(autoreset=True)
WIDTH = 42

# ---------------- DETERMINISTIC VISUAL ENGINE (MODIFIED FOR WICK CHAR) ----------------
def build_candle_bar(o, h, l, c, width=WIDTH):
    o, h, l, c = map(float, (o, h, l, c))
    rng = h - l
    if rng == 0:
        rng = 1e-9
    lower = max(0.0, min(1.0, (min(o, c) - l) / rng))
    upper = max(0.0, min(1.0, (h - max(o, c)) / rng))
    body = max(0.0, 1.0 - lower - upper)
    lower_len = int(lower * width)
    body_len = int(body * width)
    upper_len = width - lower_len - body_len
    if body_len < 1:
        body_len = 1
    if lower_len + body_len > width:
        lower_len = width - body_len
    upper_len = width - lower_len - body_len
    bar = ""
    # lower wick (Using ━)
    bar += Fore.LIGHTBLACK_EX + "━" * lower_len
    # body (Using █)
    if c > o:
        bar += Fore.GREEN + "█" * body_len
    elif o > c:
        bar += Fore.RED + "█" * body_len
    else:
        bar += Fore.YELLOW + "█" * body_len
    # upper wick (Using ━)
    bar += Fore.LIGHTBLACK_EX + "━" * upper_len
    return bar + Style.RESET_ALL

# ---------------- 42-MIN ROLLING API (MIDPOINT OPEN MODIFIED) ----------------
def get_bos_bar(df):
    try:
        if df is None or len(df) < 42:
            return Fore.LIGHTBLACK_EX + "━" * WIDTH + Style.RESET_ALL, "0.00", "NONE"
            
        # 1. Capture Cumulative 42-minute boundaries
        window = df.iloc[-42:]
        h_42 = float(window['High'].max())
        l_42 = float(window['Low'].min())
        c_42 = float(window.iloc[-1]['Close'])  # Live current close price
        
        # Override the first open with the true High-Low window midpoint
        o_42 = (h_42 + l_42) / 2.0
        
        # ⚡ PURE STRUCTURAL BREAKOUT LOGIC GATES
        # Evaluates the live close price against the structural high/low walls of the 42-bar zone
        signal = "NONE"
        if c_42 > h_42:
            signal = "BUY"
            print(f"🚀 {Fore.GREEN}STRUCTURAL BREAKOUT: Price {c_42:.2f} Cleared Range High {h_42:.2f}")
        elif c_42 < l_42:
            signal = "SELL"
            print(f"🔴 {Fore.RED}STRUCTURAL BREAKDOWN: Price {c_42:.2f} Smashed Range Low {l_42:.2f}")
        
        # 2. Build the visual bar using modified midpoint open parameters
        visual_bar = build_candle_bar(o_42, h_42, l_42, c_42)
        
        # 3. Calculate 42-Period Simple Moving Average on Close Prices
        sma_42 = float(window['Close'].mean())
        
        # 4. EXACT PINE SCRIPT MATCH: (SMA42 + LIVE) / 2
        # Pure 50/50 split midpoint engine.
        bos_value = (sma_42 + c_42) / 2.0
        bos_str = f"{bos_value:.2f}"
        
        # Returns the geometric bar, the midpoint string, and the raw structural signal string
        return visual_bar, bos_str, signal
        
    except Exception:
        return Fore.LIGHTBLACK_EX + "━" * WIDTH + Style.RESET_ALL, "ERR", "NONE"

if __name__ == "__main__":
    # Test block template using simulated random array data
    print("\n[PXY CHART STATUS] Initializing Structural Breakout Test Run via sysbbospxy...")
    print("-" * 50)
    
    # Simulating a mock dataframe layer with required columns
    np.random.seed(42)
    mock_data = {
        "High": np.random.uniform(61000, 61100, size=50),
        "Low": np.random.uniform(60800, 60900, size=50),
        "Close": np.random.uniform(60900, 61050, size=50)
    }
    mock_df = pd.DataFrame(mock_data)
    
    # Run a test execution loop through the core engine function
    bar, val, sig = get_bos_bar(mock_df)
    print(f"• VISUAL BAR : {bar}")
    print(f"• BOS VALUE  : {val}")
    print(f"• SIGNAL STATUS : {sig}")
    print("-" * 50)



#sysexitpxy.py
import os
import pandas as pd
from syscnfgpxy import PARAMS  # Only TICKER will be used
from colorama import Fore, Style, init

# Initialize Colorama
init(autoreset=True)

# -------------------- Hardcoded constants --------------------
TOTAL_WIDTH = 42

def load_cached_data() -> pd.DataFrame:
    """
    Safely reads the already-dumped JSON matrix from your background engine,
    completely bypassing yfinance disk-caching bottlenecks.
    """
    try:
        script_directory = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
        parent_directory = os.path.dirname(script_directory)
        
        # Read the daily candle cache shared with the web charts.
        json_path = os.path.join(parent_directory, "web", "webdaypxy.json")
        
        if not os.path.exists(json_path):
            return None
            
        # Read the json file matching the 'split' orientation used by your engine
        df = pd.read_json(json_path, orient='split')
        return df
    except Exception as e:
        print(f"{Fore.RED}Error reading cache matrix: {e}")
        return None

# -------------------- Direction logic --------------------
def detect_raw_direction(df: pd.DataFrame) -> tuple:
    """
    Compares the running candle (C0) against the previous completed candle (C1).
    
    Returns:
        (latest_price, direction)
    
    Inter-Candle Structural Logic:
    - UP  : C0 Close > C1 Close
    - DOWN: C0 Close < C1 Close
    - NONE: C0 Close == C1 Close or missing data
    """
    # Ensure we have at least 2 candles to perform the comparison
    if df is None or len(df) < 2:
        return (None, "NONE")

    # Extract the last two rows (C1 and C0)
    c1_row = df.iloc[-2]  # Previous completed candle
    c0_row = df.iloc[-1]  # Current running candle

    # Assign close values
    c1_close = c1_row['Close']
    c0_close = c0_row['Close']  # Running current price

    # Evaluate dynamic direction state
    if c0_close > c1_close:
        direction = "UP"
    elif c0_close < c1_close:
        direction = "DOWN"
    else:
        direction = "NONE"

    return (c0_close, direction)

# -------------------- Self-runnable test --------------------
if __name__ == "__main__":
    # FIX: Swapped out high-disk fetch_yf_data() for fast 2ms cache parsing
    df = load_cached_data()
    price, direction = detect_raw_direction(df)

    # Convert price to integer safely using rounding logic
    price_int = int(round(price)) if price is not None else "-"

    # Apply color
    if direction == "UP":
        color = Fore.GREEN
    elif direction == "DOWN":
        color = Fore.RED
    else:
        color = Fore.YELLOW

    left_text = f"Price:{price_int}"
    right_text = f"Mullu:{direction}"

    # Color only price and direction
    left_text_colored = color + left_text + Style.RESET_ALL
    right_text_colored = color + right_text + Style.RESET_ALL

    # Calculate spacing for 42-char width
    space_width = TOTAL_WIDTH - len(left_text) - len(right_text)
    if space_width < 0:
        space_width = 1
    spacing = " " * space_width

    # Print final line
    print(left_text_colored + spacing + right_text_colored)

#sysdirpxy.py
import pandas as pd
from sysrawpxy import get_raw_oc_direction
from colorama import Fore, Style, init

# Initialize Colorama
init(autoreset=True)

# -------------------- Hardcoded constants --------------------
TOTAL_WIDTH = 42

def load_cached_data() -> pd.DataFrame:
    """Compatibility wrapper: fetch current production DTAF candles, not web cache."""
    try:
        from sysdtafpxy import fetch_yf_data
        return fetch_yf_data()
    except Exception as e:
        print(f"{Fore.RED}Error fetching DTAF market data: {e}")
        return None

# -------------------- Direction logic --------------------
def detect_raw_direction(df: pd.DataFrame) -> tuple:
    """Return the DTAF OC (C1 previous close vs C0 running close) direction."""
    return get_raw_oc_direction(df)

# -------------------- Self-runnable test --------------------
if __name__ == "__main__":
    # Fetch live production DTAF candles instead of the web JSON cache
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

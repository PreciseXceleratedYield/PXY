# syspowrpxy.py
import pandas as pd
from sysdtafpxy import fetch_yf_data
from colorama import Fore, Style, init

# Initialize Colorama
init(autoreset=True)

# -------------------- Hardcoded constants --------------------
ATR_PERIOD = 14
RAW_POWER_MAX = 3
TOTAL_WIDTH = 42

# -------------------- CE/PE Power Calculation --------------------
def get_ce_pe_power(df=None):
    if df is None:
        df = fetch_yf_data(period="2d", interval="1m")
        
    """
    Calculate CE/PE power based on last move and ATR using 1-min data.
    Returns:
        direction (str): 'Up', 'Down', 'Flat'
        CEPower (int): 1-5
        PEPower (int): 1-5
    """
    # Fetch data: fallback if insufficient rows
    df = fetch_yf_data(period="2d", interval="1m")
    if df.empty or len(df) < 2:
        df = fetch_yf_data(period="5d", interval="1m")
    if df.empty or len(df) < 2:
        return "Flat", 1, 1  # fallback

    df = df[['Open','High','Low','Close']].astype(float).copy()

    # ATR calculation
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift(1)).abs()
    low_close = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(ATR_PERIOD, min_periods=1).mean()

    # Last move
    last_move = float(df['Close'].iloc[-1] - df['Close'].iloc[-2])
    raw_power = abs(last_move / atr.iloc[-1])

    # Scale 1-5 (Maintains identical underlying momentum sensitivity)
    scaled_power = int(raw_power / RAW_POWER_MAX * 5)
    scaled_power = max(1, min(scaled_power, 5))

    # Determine direction and powers
    if last_move > 0:
        direction = "Up"
        CEPower = scaled_power
        PEPower = 1
    elif last_move < 0:
        direction = "Down"
        CEPower = 1
        PEPower = scaled_power
    else:
        direction = "Flat"
        CEPower = 1
        PEPower = 1

    return direction, CEPower, PEPower

# -------------------- Self-runnable test --------------------
if __name__ == "__main__":
    direction, CEPower, PEPower = get_ce_pe_power()

    # Color coding
    ce_color = Fore.YELLOW if CEPower > 1 else Fore.WHITE
    pe_color = Fore.YELLOW if PEPower > 1 else Fore.WHITE

    # Labels and values
    left_text = f"CE Power:{CEPower}"
    right_text = f"PE Power:{PEPower}"

    left_text_colored = "CE Power:" + ce_color + str(CEPower) + Style.RESET_ALL
    right_text_colored = "PE Power:" + pe_color + str(PEPower) + Style.RESET_ALL

    # Compute spacing for total width = 42
    space_width = TOTAL_WIDTH - len(left_text) - len(right_text)
    if space_width < 0:
        space_width = 1
    spacing = " " * space_width

    # Print single line
    print(left_text_colored + spacing + right_text_colored)


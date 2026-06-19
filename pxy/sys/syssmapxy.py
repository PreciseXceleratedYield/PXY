# Save this file as syssmapxy.py
import pandas as pd
import numpy as np
import warnings
from colorama import Fore, Style, init

warnings.simplefilter(action='ignore', category=FutureWarning)
init(autoreset=True)

from sysdtafpxy import fetch_yf_data

def get_sma(df: pd.DataFrame, period: int = 42) -> dict:
    """ 
    Standard Fixed 42-SMA Trend System. 
    Generates binary direction states (NORTH/SOUTH) based on SMA relative position.
    """
    if df is None or df.empty or len(df) < period:
        return {"value": 0.0, "status": "NA", "period": period}

    df = df.copy()
    df['SMA'] = df['Close'].rolling(window=period).mean()
    
    close_arr = df['Close'].to_numpy()
    sma_arr = df['SMA'].to_numpy()
    
    # Extract latest valid calculations
    latest_close = close_arr[-1]
    latest_sma = sma_arr[-1]

    if np.isnan(latest_sma):
        return {"value": 0.0, "status": "NA", "period": period}

    # Strict binary mapping based on current location relative to SMA
    status = "NORTH" if latest_close >= latest_sma else "SOUTH"

    return {
        "value": float(latest_sma),
        "status": status,
        "period": period
    }

if __name__ == "__main__":
    df = fetch_yf_data()
    
    if df is not None and not df.empty:
        result = get_sma(df, period=42) 
        
        if result["status"] == "NORTH":
            color = Fore.GREEN + Style.BRIGHT
            output = "🟢 PRICE MOVING NORTH 🟢".center(40)
        elif result["status"] == "SOUTH":
            color = Fore.RED + Style.BRIGHT
            output = "🔴 PRICE MOVING SOUTH 🔴".center(40)
        else:
            color = Fore.WHITE
            output = "PRICE DIRECTION UNKNOWN".center(40)
            
        print(f"\n{color}{output}{Style.RESET_ALL}\n")


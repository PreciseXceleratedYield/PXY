# Save this file as syssmapxy.py
import pandas as pd
import numpy as np
import warnings
import os
from colorama import Fore, Style, init

warnings.simplefilter(action='ignore', category=FutureWarning)
init(autoreset=True)

from sysdtafpxy import fetch_yf_data

def get_sma(df: pd.DataFrame, period: int = 42) -> dict:
    """Standard Fixed 42-SMA Trend System. Generates binary direction states (NORTH/SOUTH) based on SMA relative position."""
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
        "period": period,
        "df_with_sma": df  # Return df to pass to json exporter
    }

def dump_ohlc_json(df: pd.DataFrame, target_folder_name: str = "web") -> None:
    """
    Constructs a custom 42-period trend-tracking candle.
    O = Latest 42-SMA value
    H = Highest price point across the LAST 42 candles
    L = Lowest price point across the LAST 42 candles
    C = Current Live / Close price
    """
    if df is None or df.empty or 'SMA' not in df.columns:
        print("Invalid data. Cannot dump single candle JSON.")
        return
        
    # 1. Grab the last 42 rows to find the absolute range boundaries
    window_42 = df.iloc[-42:]
    
    # 2. Extract the latest single row for Open (SMA) and Close (Live)
    latest_row = df.iloc[-1]
    
    # 3. Calculate highest and lowest points across the full 42-candle window
    highest_price = window_42['High'].max()
    lowest_price = window_42['Low'].min()
    
    # Construct the tracking candle dictionary
    candle_data = [{
        'O': float(latest_row['SMA']),     # SMA price is open
        'H': float(highest_price),         # Highest price point in 42 candles
        'L': float(lowest_price),          # Lowest price point in 42 candles
        'C': float(latest_row['Close'])    # Live price is close
    }]
    
    # Build absolute paths for sibling folder 'web'
    base_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(base_dir)
    sibling_dir = os.path.join(parent_dir, target_folder_name)
    
    # Ensure sibling folder exists
    os.makedirs(sibling_dir, exist_ok=True)
    
    # Save (always replaces existing file)
    json_path = os.path.join(sibling_dir, 'websmapxy.json')
    
    # Dump directly using pandas frame
    pd.DataFrame(candle_data).to_json(json_path, orient='records', indent=4)
    print(f"Custom Trend Candle replaced successfully at: {json_path}")

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
        
        # Dump the custom window row to the 'web' folder
        if "df_with_sma" in result:
            dump_ohlc_json(result["df_with_sma"], target_folder_name="web")


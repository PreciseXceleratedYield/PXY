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

def dump_ohlc_json(df: pd.DataFrame, target_folder_name: str = "SiblingFolderName") -> None:
    """
    Constructs a single-candle OHLC row using the latest data point.
    O = Latest SMA, H = Latest High, L = Latest Low, C = Latest Close.
    Overwrites websmapxy.json in the sibling directory.
    """
    if df is None or df.empty or 'SMA' not in df.columns:
        print("Invalid data. Cannot dump single candle JSON.")
        return
        
    # Extract only the last row for a single candle
    latest_row = df.iloc[-1]
    
    # Construct the single row dictionary
    candle_data = [{
        'O': float(latest_row['SMA']),
        'H': float(latest_row['High']),
        'L': float(latest_row['Low']),
        'C': float(latest_row['Close'])
    }]
    
    # Build absolute paths for sibling folder
    base_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(base_dir)
    sibling_dir = os.path.join(parent_dir, target_folder_name)
    
    # Ensure sibling folder exists
    os.makedirs(sibling_dir, exist_ok=True)
    
    # Save (always replaces existing file)
    json_path = os.path.join(sibling_dir, 'websmapxy.json')
    
    # Dump directly using pandas frame to match formatting
    pd.DataFrame(candle_data).to_json(json_path, orient='records', indent=4)
    print(f"Candle data replaced successfully at: {json_path}")

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
        
        # Dump the single latest row to the sibling folder
        if "df_with_sma" in result:
            dump_ohlc_json(result["df_with_sma"], target_folder_name="SiblingFolderName")



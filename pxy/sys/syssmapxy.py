# ===============================================================================
# FIXED 42-PERIOD SIMPLE MOVING AVERAGE PIPELINE ENGINE (BUY/SELL/BULL/BEAR)
# ===============================================================================
# syssmapxy.py
import pandas as pd
import numpy as np
import warnings
from colorama import Fore, Style, init

# Silence future warning constraints completely
warnings.simplefilter(action='ignore', category=FutureWarning)
init(autoreset=True)

# ---- Pure Production Naming Alignment Imports ----
from sysdtafpxy import fetch_yf_data

def get_sma(df: pd.DataFrame, period: int = 42) -> dict:
    """ 
    Standard Fixed 42-SMA Trend System. 
    Generates single-bar breakout alerts (BUY/SELL) and tracking regimes (BULL/BEAR).
    """
    if df is None or df.empty or len(df) < period:
        return {"value": 0.0, "status": "NA", "period": period}

    df = df.copy()

    # 1. Clean Vectorized Rolling SMA Calculation
    df['SMA'] = df['Close'].rolling(window=period).mean()
    
    # Extract underlying numpy arrays for execution loop
    close_arr = df['Close'].to_numpy()
    sma_arr = df['SMA'].to_numpy()
    n = len(df)
    
    # 2. Asymmetric State Processing Loop across entire history
    sma_trend_history = []
    
    for i in range(n):
        # Handle early cold-start padding rows before the moving average window prints
        if np.isnan(sma_arr[i]):
            sma_trend_history.append("NA")
            continue
            
        # Determine raw baseline status for the current index
        raw_regime = "BULL" if close_arr[i] >= sma_arr[i] else "BEAR"
        
        # If it's the very first row that calculated a valid SMA, assign base regime directly
        if i < 1 or sma_trend_history[i-1] == "NA":
            sma_trend_history.append(raw_regime)
            continue
            
        # Extract the true previous raw direction state to check for trend changes
        # Re-evaluates past raw crosses accurately instead of getting locked on BUY/SELL labels
        prev_close = close_arr[i-1]
        prev_sma = sma_arr[i-1]
        prev_raw_regime = "BULL" if (np.isnan(prev_sma) or prev_close >= prev_sma) else "BEAR"
        
        # --- PIPELINE GATING: BREAKOUT SIGNALS ---
        cross_buy  = (raw_regime == "BULL") and (prev_raw_regime == "BEAR")
        cross_sell = (raw_regime == "BEAR") and (prev_raw_regime == "BULL")
        
        if cross_buy:
            sma_trend_history.append("BUY")
        elif cross_sell:
            sma_trend_history.append("SELL")
        else:
            sma_trend_history.append(raw_regime)

    # Bind historical tracking lists clean back to DataFrame column schema
    df['sma_trend_full'] = sma_trend_history

    # 3. Extract Latest Endpoints Safely
    latest_sma = df['SMA'].iloc[-1]
    status = df['sma_trend_full'].iloc[-1]

    if np.isnan(latest_sma):
        return {"value": 0.0, "status": "NA", "period": period}

    return {
        "value": float(latest_sma),
        "status": status,
        "period": period
    }

# ===============================================================================
# 🚀 REAL DATA PRODUCTION SELF TEST RUNNER
# ===============================================================================
if __name__ == "__main__":
    print("[SYSTEM] Initializing 42 SMA state-switch engine test...")
    
    # Sync with live historical engine frame
    df = fetch_yf_data()
    
    if df is not None and not df.empty:
        # Run fixed 42 parameter tracking structure
        result = get_sma(df, period=42) 
        
        color = {
            "BUY": Fore.GREEN + Style.BRIGHT,
            "BULL": Fore.GREEN,
            "SELL": Fore.RED + Style.BRIGHT,
            "BEAR": Fore.RED,
            "NA": Fore.WHITE
        }.get(result["status"], Fore.WHITE)
        
        line = f"SMA({result['period']}): {result['status']} | VAL: {result['value']:.2f}"
        print(f"\n{color}{line}{Style.RESET_ALL}\n")
    else:
        print("[CRITICAL] Real-data feed returned empty frame matrix.")


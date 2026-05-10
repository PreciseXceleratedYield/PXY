import yfinance as yf
import pandas as pd
import numpy as np

def get_entry_signal():
    """
    Fetches NIFTY 50 data and returns the current Entry and Exit status.
    V5 logic with V2 Taxation + Dynamic ATR-based 3/7 targets.
    """
    ticker_symbol = "^NSEI"
    
    try:
        df = yf.download(ticker_symbol, period='5d', interval='1m', progress=False)
        if df.empty or len(df) < 210:
            return "NONE", "NONE"
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        close_ser = df['Close'].squeeze()
        open_ser = df['Open'].squeeze()
        high_ser = df['High'].squeeze()
        low_ser = df['Low'].squeeze()
    except Exception:
        return "NONE", "NONE"

    # ==========================================
    # 1. TREND & DYNAMIC TARGET CALCULATIONS
    # ==========================================
    df['sma200'] = close_ser.rolling(window=200).mean()
    
    tr = pd.concat([
        (high_ser - low_ser),
        (high_ser - close_ser.shift(1)).abs(),
        (low_ser - close_ser.shift(1)).abs()
    ], axis=1).max(axis=1)
    
    df['atr'] = tr.rolling(window=14).mean()
    df['smoothed_atr'] = df['atr'].rolling(window=14).mean()

    # Dynamic Requirements (ATR/3 and Full ATR)
    # Target counts scale with volatility, minimum 3 and 7
    df['trend_target'] = (df['smoothed_atr'] / 3).fillna(3).round().clip(lower=3).astype(int)
    df['counter_target'] = df['smoothed_atr'].fillna(7).round().clip(lower=7).astype(int)

    # P-Master Dots System
    df['ohlc4'] = (open_ser + high_ser + low_ser + close_ser) / 4
    df['p_price'] = ((close_ser + (close_ser + close_ser.shift(1))/2 + (close_ser + open_ser)/2 + df['ohlc4']) / 4).round(4)
    df['p_change'] = df['p_price'].diff()

    # ==========================================
    # 2. V2 TAXATION COUNTER ENGINE
    # ==========================================
    green_counts = np.zeros(len(df))
    red_counts = np.zeros(len(df))
    g, r = 0, 0
    p_change_vals = df['p_change'].values

    for i in range(1, len(df)):
        change = p_change_vals[i]
        if change >= 0:
            g += 1
            if r == 1: r, g = 0, max(0, g - 2)
            elif r > 1: r = 0
        else:
            r += 1
            if g == 1: g, r = 0, max(0, r - 2)
            elif g > 1: g = 0
        green_counts[i], red_counts[i] = g, r

    # ==========================================
    # 3. ENTRY LOGIC (Closed Bar: -2)
    # ==========================================
    idx = -2
    dyn_len = int(max(10, round(df['smoothed_atr'].iloc[idx])))
    atr_sma = close_ser.iloc[idx - dyn_len + 1 : idx + 1].mean()
    
    isBull = atr_sma > df['sma200'].iloc[idx]
    isBear = atr_sma < df['sma200'].iloc[idx]
    
    flippedG = (p_change_vals[idx] >= 0) and (p_change_vals[idx-1] < 0)
    flippedR = (p_change_vals[idx] < 0) and (p_change_vals[idx-1] >= 0)
    
    # Check counts from previous bar against Dynamic Targets
    pR, pG = red_counts[idx-1], green_counts[idx-1]
    t_req = df['trend_target'].iloc[idx]
    c_req = df['counter_target'].iloc[idx]

    entry = "NONE"
    if isBull and t_req <= pR < c_req and flippedG:
        entry = "OTMBUY"
    elif isBear and t_req <= pG < c_req and flippedR:
        entry = "OTMSELL"
    elif isBear and pR >= c_req and flippedG:
        entry = "ATMBUY"
    elif isBull and pG >= c_req and flippedR:
        entry = "ATMSELL"

    # ==========================================
    # 4. EXIT LOGIC (Live Bar: -1)
    # ==========================================
    p0 = round(((close_ser.iloc[-1] + (close_ser.iloc[-2] + close_ser.iloc[-1])/2 + (close_ser.iloc[-1] + open_ser.iloc[-1])/2 + df['ohlc4'].iloc[-1]) / 4), 4)
    p1 = df['p_price'].iloc[-2]
    
    exit_sig = "BULL" if p0 > p1 else "BEAR"
    
    # Sync Entry to Exit if no specific V5 signal
    if entry == "NONE":
        entry = exit_sig

    return entry, exit_sig


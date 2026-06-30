import warnings 
import numpy as np 
import pandas as pd 
import yfinance as yf 
from syscnfgpxy import TICKER, OHLC_MODE, TIMEZONE 

warnings.simplefilter(action='ignore', category=FutureWarning)

def apply_ohlc_transformation(df, mode=1):
    """Passes through raw arrays unchanged for Mode 1"""
    if df.empty:
        return df
        
    if mode != 1:
        print(f"SYSTEM_WARNING | Mode {mode} unrecognized. Defaulting to Mode 1 Raw Candles.")
        
    # Mode 1 is strictly pure raw candles (No alterations)
    return df

def detect_oc2_patterns(df):
    """
    Detects Bullish and Bearish OC/2 patterns based on Body Open/Close relationships.
    Adds 'OC2_Signal' column: 1 for Bullish, -1 for Bearish, 0 for None.
    """
    if df.empty or len(df) < 2:
        df['OC2_Signal'] = 0
        return df

    # Shifted values to reference the previous candle (candle 1)
    prev_open = df['Open'].shift(1)
    prev_close = df['Close'].shift(1)
    
    current_open = df['Open']
    current_close = df['Close']

    # Define bullish and bearish states for candles
    is_prev_bearish = prev_close < prev_open
    is_prev_bullish = prev_close > prev_open
    is_curr_bullish = current_close > current_open
    is_curr_bearish = current_close < current_open

    # OC/2 Logic Conditions
    # Bullish: Previous was Red, Current is Green, Current Open <= Previous Close, Current Close >= Previous Open
    bullish_oc2 = is_prev_bearish & is_curr_bullish & (current_open <= prev_close) & (current_close >= prev_open)
    
    # Bearish: Previous was Green, Current is Red, Current Open >= Previous Close, Current Close <= Previous Open
    bearish_oc2 = is_prev_bullish & is_curr_bearish & (current_open >= prev_close) & (current_close <= prev_open)

    # Initialize signal array
    conditions = [bullish_oc2, bearish_oc2]
    choices = [1, -1] # 1 = Bullish OC/2, -1 = Bearish OC/2
    
    df['OC2_Signal'] = np.select(conditions, choices, default=0)
    return df

def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """DYNAMIC HISTORICAL SLICE RETRIEVAL ENGINE FOR RAW MODE 1 DATA WITH OC/2 DETECTION"""
    ticker_obj = yf.Ticker(TICKER)
    df = pd.DataFrame()
    
    # Warmup window to accommodate the 42 SMA calculation smoothly
    buffer_rows = target_rows + 45

    if period is not None:
        try:
            df = ticker_obj.history(period=period, interval=interval)
        except Exception as e:
            print(f"ERROR: Explicit download failed for period={period} | {e}")
            
    if df.empty:
        for search_period in ["5d", "7d", "max"]:
            try:
                df = ticker_obj.history(period=search_period, interval=interval)
                if not df.empty:
                    df.dropna(inplace=True)
                    if len(df) >= buffer_rows:
                        break
            except Exception:
                pass
                
    if df.empty or len(df) < buffer_rows:
        print(f"CRITICAL: Failed to collect minimum {buffer_rows} candles.")
        return pd.DataFrame()
        
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
        
    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(TIMEZONE)
    else:
        df = df.tz_convert(TIMEZONE)
        
    processed_df = apply_ohlc_transformation(df.copy(), mode=OHLC_MODE)
    
    # Calculate 42 SMA directly on the raw closing prices
    processed_df['SMA_42'] = processed_df['Close'].rolling(window=42).mean()
    
    # Inject the OC/2 pattern detection before slicing out the final tails
    processed_df = detect_oc2_patterns(processed_df)
    
    return processed_df.tail(target_rows)


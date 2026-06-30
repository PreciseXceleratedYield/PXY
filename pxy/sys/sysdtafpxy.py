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

def transform_to_oc2_candles(df):
    """
    Transforms the OHLC structure into custom OC/2 candles:
    - Present Open  = Previous Candle's (Open + Close) / 2
    - Present Close = Present Candle's (Open + Close) / 2
    """
    if df.empty or len(df) < 2:
        return df

    # 1. Calculate raw midpoints for every row
    raw_midpoint = (df['Open'] + df['Close']) / 2

    # 2. Map the structural modifications
    df['Custom_Close'] = raw_midpoint
    df['Custom_Open'] = raw_midpoint.shift(1)  # The present open is the previous candle's OC/2

    # 3. Clean up the very first row since it won't have a previous candle
    # Using .iloc[0] safely updates the fallback using native raw open price
    df.iloc[0, df.columns.get_loc('Custom_Open')] = df.iloc[0, df.columns.get_loc('Open')]

    # 4. Readjust High and Low so wicks don't cut through the newly calculated body boundaries
    df['Custom_High'] = df[['High', 'Custom_Open', 'Custom_Close']].max(axis=1)
    df['Custom_Low'] = df[['Low', 'Custom_Open', 'Custom_Close']].min(axis=1)

    # 5. Overwrite the standard OHLC columns so your downstream system reads the clean custom candles natively
    df['Open'] = df['Custom_Open']
    df['High'] = df['Custom_High']
    df['Low'] = df['Custom_Low']
    df['Close'] = df['Custom_Close']

    # 6. Drop temporary columns to keep the final output DataFrame clean
    df.drop(columns=['Custom_Open', 'Custom_High', 'Custom_Low', 'Custom_Close'], inplace=True)

    return df

def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """DYNAMIC HISTORICAL SLICE RETRIEVAL ENGINE FOR CUSTOM OC/2 MATHEMATICAL CANDLES"""
    ticker_obj = yf.Ticker(TICKER)
    df = pd.DataFrame()
    
    # Warmup window adjusted (+47) to accommodate both SMA_42 and the candle .shift(1) smoothly
    buffer_rows = target_rows + 47

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
    
    # Calculate 42 SMA directly on the raw closing prices before custom candle transformation
    processed_df['SMA_42'] = processed_df['Close'].rolling(window=42).mean()
    
    # Apply your custom OC/2 candle transformation to the matrix
    processed_df = transform_to_oc2_candles(processed_df)
    
    return processed_df.tail(target_rows)

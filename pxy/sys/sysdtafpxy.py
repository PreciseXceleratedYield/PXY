import warnings 
import numpy as np 
import pandas as pd 
import yfinance as yf 
from syscnfgpxy import TICKER, OHLC_MODE, TIMEZONE 

warnings.simplefilter(action='ignore', category=FutureWarning)

def calculate_tsma(series, period=7):
    """Calculates Time Series Moving Average (Least Squares Linear Regression line end point)"""
    if len(series) < period:
        return np.nan
    
    # Pre-create x coordinates for the linear regression
    x = np.arange(period)
    
    def get_reg_endpoint(y):
        # Fits y = mx + c and solves for the final point (x = period - 1)
        slope, intercept = np.polyfit(x, y, 1)
        return slope * (period - 1) + intercept

    # Apply the rolling window regression endpoint extraction
    return series.rolling(window=period).apply(get_reg_endpoint, raw=True)

def apply_ohlc_transformation(df, mode=1):
    """Handles Mode 1 (Raw) and Mode 2 (TSMA Balanced Hybrid Average)"""
    if df.empty:
        return df
        
    if mode == 2:
        print("SYSTEM_INFO | Applying Mode 2: Real OHLC & 7-Period TSMA Average Transformation.")
        
        # 1. Calculate the standalone 7-period TSMA for each individual metric
        tsma_open  = calculate_tsma(df['Open'], period=7)
        tsma_high  = calculate_tsma(df['High'], period=7)
        tsma_low   = calculate_tsma(df['Low'], period=7)
        tsma_close = calculate_tsma(df['Close'], period=7)
        
        # 2. Average the Real OHLC with their corresponding TSMA metrics
        df['Open']  = (df['Open'] + tsma_open) / 2
        df['High']  = (df['High'] + tsma_high) / 2
        df['Low']   = (df['Low'] + tsma_low) / 2
        df['Close'] = (df['Close'] + tsma_close) / 2
        
        # Drop rows that don't have enough data to generate the 7-period TSMA
        df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
        
    elif mode != 1:
        print(f"SYSTEM_WARNING | Mode {mode} unrecognized. Defaulting to Mode 1 Raw Candles.")
        
    return df

def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """DYNAMIC HISTORICAL SLICE RETRIEVAL ENGINE FOR DATA WITH OHLC MODES"""
    ticker_obj = yf.Ticker(TICKER)
    df = pd.DataFrame()
    
    # Buffer rows expanded to smoothly process both 7 TSMA and subsequent 42 SMA 
    buffer_rows = target_rows + 55

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
        
    # Transformation engine runs here (Modifies OHLC metrics if OHLC_MODE == 2)
    processed_df = apply_ohlc_transformation(df.copy(), mode=OHLC_MODE)
    
    # Calculate 42 SMA directly on the newly transformed closing prices
    processed_df['SMA_42'] = processed_df['Close'].rolling(window=42).mean()
    
    return processed_df.tail(target_rows)


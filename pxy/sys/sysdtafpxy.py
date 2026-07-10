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
    
    x = np.arange(period)
    
    def get_reg_endpoint(y):
        slope, intercept = np.polyfit(x, y, 1)
        return slope * (period - 1) + intercept

    return series.rolling(window=period).apply(get_reg_endpoint, raw=True)

def apply_ohlc_transformation(df, mode=1):
    """Handles Mode 1 (Raw) and Mode 2 (TSMA Balanced Hybrid Average)"""
    if df.empty:
        return df
        
    if mode == 2:
        tsma_open  = calculate_tsma(df['Open'], period=7)
        tsma_high  = calculate_tsma(df['High'], period=7)
        tsma_low   = calculate_tsma(df['Low'], period=7)
        tsma_close = calculate_tsma(df['Close'], period=7)
        
        df['Open']  = (df['Open'] + tsma_open) / 2
        df['High']  = (df['High'] + tsma_high) / 2
        df['Low']   = (df['Low'] + tsma_low) / 2
        df['Close'] = (df['Close'] + tsma_close) / 2
        
        df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
        
    return df

def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """DYNAMIC HISTORICAL SLICE RETRIEVAL ENGINE FOR DATA WITH OHLC MODES"""
    ticker_obj = yf.Ticker(TICKER)
    df = pd.DataFrame()
    
    buffer_rows = target_rows + 55

    if period is not None:
        try:
            df = ticker_obj.history(period=period, interval=interval)
        except Exception:
            pass
            
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
        return pd.DataFrame()
        
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
        
    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(TIMEZONE)
    else:
        df = df.tz_convert(TIMEZONE)
        
    processed_df = apply_ohlc_transformation(df.copy(), mode=OHLC_MODE)
    
    processed_df['SMA_42'] = processed_df['Close'].rolling(window=42).mean()
    
    return processed_df.tail(target_rows)

import pandas as pd
import numpy as np

def rma(series, length):
    """TradingView Running Moving Average (RMA) logic"""
    alpha = 1 / length
    result = np.zeros_like(series)
    for i in range(len(series)):
        if i == 0:
            result[i] = series[i]
        else:
            result[i] = alpha * series[i] + (1 - alpha) * result[i-1]
    return result

def get_linreg(series_slice):
    """Pine Script ta.linreg logic"""
    length = len(series_slice)
    if length < 2: return series_slice[-1]
    x = np.arange(length)
    slope, intercept = np.polyfit(x, series_slice, 1)
    return slope * (length - 1) + intercept

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['prev_close'] = df['Close'].shift(1)
    df['TR'] = np.maximum(df['High'] - df['Low'], 
               np.maximum(abs(df['High'] - df['prev_close']), 
                          abs(df['Low'] - df['prev_close'])))
    df['HL2'] = (df['High'] + df['Low']) / 2
    
    # SYNC: Using RMA for the base ATR
    df['ATR_base'] = rma(df['TR'].fillna(0).values, 14)

    size = len(df)
    st_line = np.zeros(size)
    trend = np.ones(size)

    for i in range(size):
        if i == 0:
            st_line[i] = df['HL2'].iloc[i]
            continue

        # Dynamic Period: x = 14 - ATR
        dynamic_x = int(max(2, round(14 - df['ATR_base'].iloc[i])))
        
        # TSMA Volatility via Linreg
        if i >= dynamic_x:
            tr_slice = df['TR'].iloc[i - dynamic_x + 1 : i + 1].values
            tsma_vol = get_linreg(tr_slice)
        else:
            tsma_vol = df['TR'].iloc[:i+1].mean()

        upper_band = df['HL2'].iloc[i] + (3.0 * tsma_vol)
        lower_band = df['HL2'].iloc[i] - (3.0 * tsma_vol)
        
        # Continuous Trailing Logic
        prev_st = st_line[i-1]
        if df['Close'].iloc[i] > prev_st:
            trend[i] = 1
        elif df['Close'].iloc[i] < prev_st:
            trend[i] = -1
        else:
            trend[i] = trend[i-1]

        st_line[i] = max(lower_band, prev_st) if trend[i] == 1 else min(upper_band, prev_st)

    df['ST'] = st_line
    df['ST_Trend'] = ["UP" if t == 1 else "DOWN" for t in trend]
    return df






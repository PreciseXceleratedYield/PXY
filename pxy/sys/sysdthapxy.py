# pxy_engine.py
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

def get_pxy_data(tickerSymbol=None, df=None, live_tick=None):
    """
    Transforms data into pure Heikin-Ashi (HA).
    Accepts an active live_tick dictionary to update the running candle in real-time.
    Colors candles based on Close-to-Close momentum logic.
    """
    if df is None:
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return None, None, None, pd.DataFrame()
        
    # Safeguard: Separate processing safely from global reference memory
    df = df.copy()
    
    required_cols = ['Open', 'High', 'Low', 'Close']
    for col in required_cols:
        if col not in df.columns:
            return None, None, None, pd.DataFrame()

    # LIVE TICK INJECTION: Mutate the running candle row with streaming data
    if live_tick is not None:
        last_idx = df.index[-1]
        df.loc[last_idx, 'Open'] = live_tick['Open']
        df.loc[last_idx, 'High'] = max(live_tick['High'], live_tick['Close'])
        df.loc[last_idx, 'Low'] = min(live_tick['Low'], live_tick['Close'])
        df.loc[last_idx, 'Close'] = live_tick['Close']  # Real-time ticking price

    # Extract values as numpy arrays for rapid iteration
    raw_open = df['Open'].values
    raw_high = df['High'].values
    raw_low = df['Low'].values
    raw_close = df['Close'].values
    
    n = len(df)
    ha_open = np.zeros(n)
    ha_close = np.zeros(n)

    # 1. Calculate Pure HA Close first (Average of current OHLC)
    ha_close = (raw_open + raw_high + raw_low + raw_close) / 4.0

    # 2. Calculate Pure HA Open recursively
    ha_open = (raw_open + raw_close) / 2.0
    for i in range(1, n):
        ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2.0

    # 3. Calculate Pure HA High and Low
    ha_high = np.maximum(raw_high, np.maximum(ha_open, ha_close))
    ha_low = np.minimum(raw_low, np.minimum(ha_open, ha_close))

    # ==================================================
    # 🕯️ BUILD CUSTOM RUNNING DATAFRAME
    # ==================================================
    custom_df = pd.DataFrame(index=df.index)
    custom_df['Open'] = ha_open
    custom_df['High'] = ha_high
    custom_df['Low'] = ha_low
    custom_df['Close'] = ha_close

    # ==================================================
    # 🎨 COLOR PROCESSING (PURE HA CLOSE VS PREVIOUS HA CLOSE)
    # ==================================================
    # Shift the Close array to get the previous candle's close for every row
    prev_ha_close_series = custom_df['Close'].shift(1)
    
    # MOMENTUM COLOR MATRIX: Green when current HA Close >= previous HA Close
    is_green = custom_df['Close'] >= prev_ha_close_series
    custom_df["pxy_color"] = np.select([is_green], ["green"], default="red")
    
    # Seed the first index color safely since shift(1) leaves row 0 as NaN
    custom_df.iloc[0, custom_df.columns.get_loc('pxy_color')] = "green" if ha_close[0] >= ha_open[0] else "red"

    # ==================================================
    # 🛡️ PRODUCTION OUTPUT FILTER (SAME SIGNATURE PASSTHROUGH)
    # ==================================================
    final_df = custom_df.copy()
    pxy_close = final_df['Close'].copy()  
    pxy_open = final_df['Open'].copy()    
    pxy_color_series = final_df['pxy_color'].copy()
    
    return pxy_close, pxy_open, pxy_color_series, final_df






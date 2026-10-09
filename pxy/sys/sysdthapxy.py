# pxy_engine.py
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data


def get_close_direction_series(closes):
    """Return each close's direction relative to the preceding close."""
    close_series = pd.to_numeric(pd.Series(closes), errors="coerce")
    changes = close_series.diff()
    return pd.Series(
        np.select(
            [changes > 0, changes < 0, changes == 0],
            ["UP", "DOWN", "FLAT"],
            default="UNKNOWN",
        ),
        index=close_series.index,
        name="pxy_direction",
    )


def get_pxy_data(tickerSymbol=None, df=None, live_tick=None):
    """
    Processes raw market OHLC candles.
    Accepts an active live_tick dictionary to update the running candle in real-time.
    Colors candles based on running Close vs the previous candle's static Close.
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

    # 🚨 LIVE TICK INJECTION: Mutate the running candle row with raw streaming market data
    if live_tick is not None:
        last_idx = df.index[-1]
        df.loc[last_idx, 'Open'] = live_tick['Open']
        df.loc[last_idx, 'High'] = max(live_tick['High'], live_tick['Close'])
        df.loc[last_idx, 'Low'] = min(live_tick['Low'], live_tick['Close'])
        df.loc[last_idx, 'Close'] = live_tick['Close']  # Real-time ticking price

    # ==================================================
    # 🕯️ BUILD RAW MARKET RUNNING DATAFRAME
    # ==================================================
    custom_df = pd.DataFrame(index=df.index)
    custom_df['Open'] = df['Open'].values
    custom_df['High'] = df['High'].values
    custom_df['Low'] = df['Low'].values
    custom_df['Close'] = df['Close'].values
    custom_df["pxy_direction"] = get_close_direction_series(custom_df["Close"])

    # ==================================================
    # 🎨 COLOR PROCESSING (RUNNING CLOSE VS PREVIOUS CLOSE)
    # ==================================================
    # Shift the Close array to get the previous candle's static close for every row
    prev_close_series = custom_df['Close'].shift(1)
    
    # Color rule: Green when running Close >= previous candle's Close
    is_green = custom_df['Close'] >= prev_close_series
    custom_df["pxy_color"] = np.select([is_green], ["green"], default="red")
    
    # Seed the first index color safely since row 0 has no previous close (NaN)
    custom_df.iloc[0, custom_df.columns.get_loc('pxy_color')] = "green" if custom_df['Close'].iloc[0] >= custom_df['Open'].iloc[0] else "red"

    # ==================================================
    # 🛡️ PRODUCTION OUTPUT FILTER (SAME SIGNATURE PASSTHROUGH)
    # ==================================================
    final_df = custom_df.copy()
    pxy_close = final_df['Close'].copy()  
    pxy_open = final_df['Open'].copy()    
    pxy_color_series = final_df['pxy_color'].copy()
    
    return pxy_close, pxy_open, pxy_color_series, final_df

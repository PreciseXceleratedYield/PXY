# _sgnl.py
import os
import warnings
import numpy as np
import pandas as pd
import yfinance as yf

# Silence formatting warnings completely
warnings.simplefilter(action='ignore', category=FutureWarning)

# =====================================================================
# STRATEGY CORE CONSTANTS
# =====================================================================
TICKER = "^NSEI"               # Tracking NIFTY 50 Index
TIMEZONE = "Asia/Kolkata"       # Local execution context

def apply_mode_5_transformation(df):
    """Applies the dense hybrid multi-model transformation matrix."""
    if df.empty: return df
    
    o = df['Open'].to_numpy()
    h = df['High'].to_numpy()
    l = df['Low'].to_numpy()
    c = df['Close'].to_numpy()
    n = len(df)

    # Matrix Model A: Heikin-Ashi Smooth Calculation
    ha_c = (o + h + l + c) / 4
    ha_o = np.zeros_like(o)
    if n > 0: ha_o = (o + c) / 2
    for i in range(1, n):
        ha_o[i] = (ha_o[i-1] + ha_c[i-1]) / 2
    ha_h = np.maximum(h, np.maximum(ha_o, ha_c))
    ha_l = np.minimum(l, np.minimum(ha_o, ha_c))

    # Matrix Model B: Open-Close Median
    oc2 = (o + c) / 2

    # Matrix Model C: Momentum Boundaries
    c1 = np.copy(c)
    c1[1:] = c[:-1]

    # Uniform merging matrix block layer
    df['Open'] = (o + ha_o + oc2 + c1) / 4
    df['High'] = (h + ha_h + oc2 + c) / 4
    df['Low'] = (l + ha_l + oc2 + c1) / 4
    df['Close'] = (c + ha_c + oc2 + c) / 4
    return df

def calculate_no_repaint_signals(df):
    """
    Evaluates trends directly from CLOSED, FIXED 1-minute Mode 5 candles.
    Completely prevents re-painting by comparing index -2 and index -3.
    """
    if df.empty or len(df) < 3:
        return 0.0, "NONE"

    opens = df['Open'].to_numpy()
    closes = df['Close'].to_numpy()

    # The actual order execution price is taken from the latest live tick (Index -1)
    live_ltp = float(closes[-1])

    # --- STRICT NO-REPAINT CLOSED CANDLE BOUNDARIES (1-MIN TIMEFRAME) ---
    # Confirmed Last Closed Candle (Index -2)
    confirmed_is_bullish = closes[-2] >= opens[-2]
    
    # Confirmed Prior Closed Candle (Index -3)
    previously_confirmed_is_bullish = closes[-3] >= opens[-3]

    # --- THE ABSOLUTE FLIP SIGNAL MATRIX ---
    if confirmed_is_bullish and not previously_confirmed_is_bullish:
        signal = "BUY"   # The closed 1-min candle flipped Bearish -> Bullish
    elif not confirmed_is_bullish and previously_confirmed_is_bullish:
        signal = "SELL"  # The closed 1-min candle flipped Bullish -> Bearish
    elif confirmed_is_bullish:
        signal = "BULL"  # Trend remains locked in a Green state
    else:
        signal = "BEAR"  # Trend remains locked in a Red state

    return live_ltp, signal

def get_all_data():
    """
    Downloads strictly 1 day of 1-minute bars straight from yfinance.
    Applies Mode 5 and maps out the verified no-repaint trend flips.
    """
    try:
        # Fetching strictly today's 1-minute tracking profile
        ticker_obj = yf.Ticker(TICKER)
        df = ticker_obj.history(period="1d", interval="1m")
        
        if df.empty:
            return {"entry": "NONE", "price": 0.0}

        df.dropna(inplace=True)
        df.index = pd.to_datetime(df.index).tz_convert(TIMEZONE)

        # Process historical completed rows via Mode 5 transformation matrix
        transformed_df = apply_mode_5_transformation(df.copy())
        ltp, signal = calculate_no_repaint_signals(transformed_df)
        
        return {"entry": signal, "price": ltp}

    except Exception as e:
        print(f"❌ Signal System Error: {e}")
        return {"entry": "NONE", "price": 0.0}

# Standalone execution diagnostic test
if __name__ == "__main__":
    print(f"📡 Testing 1-Day NO-REPAINT 1-Min Flip Signal Engine for: {TICKER}")
    print(get_all_data())

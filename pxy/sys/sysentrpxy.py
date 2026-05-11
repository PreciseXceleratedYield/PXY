import yfinance as yf
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, time as dt_time
from scipy.stats import linregress

VERBOSE = True

def get_entry_signal(df=None):
    try:
        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(ist).time()

        # 1. FETCH DATA
        if df is None:
            df = yf.download("^NSEI", period='7d', interval='1m', progress=False)
        if df is None or df.empty or len(df) < 50:
            return "NONE", "NONE"
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.copy()

        # 2. ATR & DYNAMIC PERIOD CALCULATION
        high_low = df['High'] - df['Low']
        high_cp = np.abs(df['High'] - df['Close'].shift(1))
        low_cp = np.abs(df['Low'] - df['Close'].shift(1))
        df['tr'] = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        
        atr_series = df['tr'].rolling(window=14).mean()
        
        # Function to calculate TSMA for a specific point in time
        def calc_tsma_at_idx(series, window):
            if len(series) < window: return series.iloc[-1]
            y = series.values
            x = np.arange(len(y))
            slope, intercept, _, _, _ = linregress(x, y)
            return slope * (len(y) - 1) + intercept

        # We need the TSMA for the current bar AND the previous bar to detect a cross
        curr_atr_p = max(2, int(round(atr_series.iloc[-1])) if not np.isnan(atr_series.iloc[-1]) else 14)
        prev_atr_p = max(2, int(round(atr_series.iloc[-2])) if not np.isnan(atr_series.iloc[-2]) else 14)

        tsma0 = calc_tsma_at_idx(df['Close'].tail(curr_atr_p), curr_atr_p)
        tsma1 = calc_tsma_at_idx(df['Close'].shift(1).tail(prev_atr_p), prev_atr_p)

        # 3. P-MASTER (Exit Logic)
        df['ohlc4'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        df['p_price'] = ((df['Close'] + (df['Close'] + df['Close'].shift(1).fillna(df['Close']))/2 + 
                          (df['Close'] + df['Open'])/2 + df['ohlc4']) / 4).round(4)
        
        exit_sig = "BULL" if df['p_price'].iloc[-1] > df['p_price'].iloc[-2] else "BEAR"

        # 4. FINAL SIGNAL LOGIC (Crossover Check)
        c0, c1 = df['Close'].iloc[-1], df['Close'].iloc[-2]

        if now_ist < dt_time(9, 17):
            entry = "MORNING"
        elif c1 <= tsma1 and c0 > tsma0:
            entry = "BUY"  # Bullish Crossover
        elif c1 >= tsma1 and c0 < tsma0:
            entry = "SELL" # Bearish Crossover
        else:
            # If no crossover, copy the P-Master Exit Signal
            entry = exit_sig

        if VERBOSE:
            print(f"[{datetime.now(ist).strftime('%H:%M:%S')}] TSMA: {tsma0:.2f} | Entry: {entry} | Exit: {exit_sig}")

        return entry, exit_sig

    except Exception as e:
        if VERBOSE: print(f"[CRITICAL] {e}")
        return "NONE", "NONE"


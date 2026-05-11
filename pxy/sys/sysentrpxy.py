import yfinance as yf
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, time as dt_time

VERBOSE = True

def get_entry_signal(df=None):
    try:
        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(ist).time()

        # 1. FETCH DATA
        if df is None:
            df = yf.download("^NSEI", period='7d', interval='1m', progress=False)

        if df is None or df.empty or len(df) < 20:
            return "NONE", "NONE"

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.copy()

        # 2. ATR & INTEGER ROUNDING
        high_low = df['High'] - df['Low']
        high_cp = np.abs(df['High'] - df['Close'].shift(1))
        low_cp = np.abs(df['Low'] - df['Close'].shift(1))
        df['tr'] = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        
        # Calculate 14-period ATR and round to Integer
        atr_series = df['tr'].rolling(window=14).mean()
        rounded_atr = int(round(atr_series.iloc[-1])) 

        # Baselines (14 periods)
        roll_h = df['High'].rolling(window=14).max().iloc[-1]
        roll_l = df['Low'].rolling(window=14).min().iloc[-1]
        curr_close = df['Close'].iloc[-1]

        # LIVE DYNAMIC LINES (Pine Logic)
        line_g = (curr_close + (roll_h + (rounded_atr/2))) / 2
        line_r = (curr_close + (roll_l - (rounded_atr/2))) / 2

        # 3. P-MASTER (Exit Logic)
        df['ohlc4'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        df['p_price'] = ((df['Close'] + (df['Close'] + df['Close'].shift(1).fillna(df['Close']))/2 + 
                          (df['Close'] + df['Open'])/2 + df['ohlc4']) / 4).round(4)
        
        p0, p1 = df['p_price'].iloc[-1], df['p_price'].iloc[-2]
        exit_sig = "BULL" if p0 > p1 else "BEAR"

        # 4. FINAL SIGNAL LOGIC
        if now_ist < dt_time(9, 17):
            entry = "MORNING"
        elif df['Low'].iloc[-1] < line_r:      # isBuy
            entry = "OTMBUY"
        elif df['High'].iloc[-1] > line_g:     # isSell
            entry = "OTMSELL"
        else:
            entry = exit_sig                   # Fallback: Copy exit signal

        if VERBOSE:
            print(f"[{datetime.now(ist).strftime('%H:%M:%S')}] ATR_Int: {rounded_atr} | Entry: {entry} | Exit: {exit_sig}")

        return entry, exit_sig

    except Exception as e:
        if VERBOSE: print(f"[CRITICAL] {e}")
        return "NONE", "NONE"


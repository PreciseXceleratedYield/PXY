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
            # period='7d' is used to bridge weekends/holidays for the ATR/TSMA calculation
            df = yf.download("^NSEI", period='7d', interval='1m', progress=False)
        
        if df is None or df.empty or len(df) < 50:
            if VERBOSE: print(f"[DEBUG] Insufficient Data. Bars: {len(df) if df is not None else 0}")
            return "NONE", "NONE"
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.copy()

        # 2. ATR & DYNAMIC PERIOD CALCULATION
        high_low = df['High'] - df['Low']
        high_cp = np.abs(df['High'] - df['Close'].shift(1))
        low_cp = np.abs(df['Low'] - df['Close'].shift(1))
        df['tr'] = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        
        # 14-period ATR
        atr_series = df['tr'].rolling(window=14).mean()
        
        # Pure NumPy Linear Regression (TSMA) - No Scipy required
        def calc_tsma_np(series, window):
            if len(series) < window: window = len(series)
            y = series.tail(window).values
            x = np.arange(len(y))
            # np.polyfit(x, y, 1) returns [slope, intercept]
            coeffs = np.polyfit(x, y, 1)
            return coeffs[0] * (len(y) - 1) + coeffs[1]

        # Calculate dynamic ATR periods for Current and Previous bars
        curr_atr_val = atr_series.iloc[-1]
        prev_atr_val = atr_series.iloc[-2]
        
        curr_p = max(2, int(round(curr_atr_val)) if not np.isnan(curr_atr_val) else 14)
        prev_p = max(2, int(round(prev_atr_val)) if not np.isnan(prev_atr_val) else 14)

        # Calculate TSMA for the current and previous candles
        tsma0 = calc_tsma_np(df['Close'], curr_p)
        tsma1 = calc_tsma_np(df['Close'].iloc[:-1], prev_p)

        # 3. P-MASTER (Exit Logic)
        df['ohlc4'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        df['p_price'] = ((df['Close'] + (df['Close'] + df['Close'].shift(1).fillna(df['Close']))/2 + 
                          (df['Close'] + df['Open'])/2 + df['ohlc4']) / 4).round(4)
        
        p0, p1 = df['p_price'].iloc[-1], df['p_price'].iloc[-2]
        exit_sig = "BULL" if p0 > p1 else "BEAR"

        # 4. FINAL SIGNAL LOGIC (Crossover detection)
        c0, c1 = df['Close'].iloc[-1], df['Close'].iloc[-2]

        if now_ist < dt_time(9, 17):
            entry = "MORNING"
        elif c1 <= tsma1 and c0 > tsma0:
            entry = "ATMBUY"  # Price crossed above TSMA
        elif c1 >= tsma1 and c0 < tsma0:
            entry = "ATMSELL" # Price crossed below TSMA
        else:
            # Fallback: If no crossover, follow the P-Master directional trend
            entry = exit_sig

        if VERBOSE:
            print(f"[{datetime.now(ist).strftime('%H:%M:%S')}] TSMA:{tsma0:.2f} | P:{curr_p} | Entry:{entry} | Exit:{exit_sig}")

        return entry, exit_sig

    except Exception as e:
        if VERBOSE: print(f"[CRITICAL] {e}")
        return "NONE", "NONE"



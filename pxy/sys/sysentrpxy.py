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
            # interval='1m' requires a short period (max 7 days)
            df = yf.download("^NSEI", period='7d', interval='1m', progress=False)

        # We need at least 15 bars (14 for rolling window + 1 for signal comparison)
        if df is None or df.empty or len(df) < 15:
            if VERBOSE: print(f"[DEBUG] Data Failure. Bars: {len(df) if df is not None else 0}")
            return "NONE", "NONE"

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.copy()

        # 2. P-MASTER CALCULATION (For Exit Logic)
        df['ohlc4'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        df['p_price'] = ((df['Close'] + (df['Close'] + df['Close'].shift(1).fillna(df['Close']))/2 + 
                          (df['Close'] + df['Open'])/2 + df['ohlc4']) / 4).round(4)
        
        p0, p1 = df['p_price'].iloc[-1], df['p_price'].iloc[-2]
        
        # EXIT SIMPLE: Simple directional bias based on p_price
        exit_sig = "BULL" if p0 > p1 else "BEAR"

        # 3. ROLLING 14m GRID LOGIC (PINE SIMPLE)
        # Replicating roll_h = ta.highest(high, 14) and roll_l = ta.lowest(low, 14)
        roll_h = df['High'].rolling(window=14).max().iloc[-1]
        roll_l = df['Low'].rolling(window=14).min().iloc[-1]

        # LIVE DYNAMIC LINES: line_g = (roll_h + close) / 2 | line_r = (roll_l + close) / 2
        line_g = (roll_h + df['Close'].iloc[-1]) / 2
        line_r = (roll_l + df['Close'].iloc[-1]) / 2

        # SIGNAL LOGIC: isBuy = low < line_r | isSell = high > line_g
        isBuy = df['Low'].iloc[-1] < line_r
        isSell = df['High'].iloc[-1] > line_g

        # 4. FINAL ENTRY/EXIT ASSIGNMENT
        if now_ist < dt_time(9, 17):
            entry = "MORNING"
        elif isBuy:
            entry = "OTMBUY"
        elif isSell:
            entry = "OTMSELL"
        else:
            # Fallback: if Pine logic is NONE, copy the exit signal
            entry = exit_sig

        if VERBOSE:
            print(f"[{datetime.now(ist).strftime('%H:%M:%S')}] Entry: {entry} | Exit: {exit_sig} | L_R: {line_r:.1f} L_G: {line_g:.1f}")

        return entry, exit_sig

    except Exception as e:
        if VERBOSE: print(f"[CRITICAL] {e}")
        return "NONE", "NONE"

# Example Usage:
# signal, exit = get_entry_signal()
# print(f"Final Signal: {signal}, Exit Bias: {exit}")

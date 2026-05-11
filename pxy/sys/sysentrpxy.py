import yfinance as yf
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, time as dt_time

# Set to True to see bar-by-bar logic in your console
VERBOSE = True 

def get_entry_signal(df=None):
    """
    V5 Logic with V2 Taxation. 
    Synced for RUNNING BARS with 9:17 AM Morning Rule.
    """
    try:
        # 1. FETCH DATA
        # Increased to 5d to ensure we always have enough bars regardless of weekends
        if df is None:
            df = yf.download("^NSEI", period='5d', interval='1m', progress=False)
        
        if df is None or df.empty or len(df) < 21:
            if VERBOSE: print(f"[DEBUG] Data Fetch Failed or Insufficient Bars. Count: {len(df) if df is not None else 0}")
            return "NONE", "NONE"

        # Standardise yfinance columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.copy()

        # ==========================================
        # 2. SESSION DATA (Zero Lag Trend - Sync with Pine)
        # ==========================================
        df.index = pd.to_datetime(df.index)
        # Detect New Day (Pine's ta.change(time("D")))
        is_new_day = df.index.date != np.roll(df.index.date, 1)
        
        s_high = np.zeros(len(df))
        s_low = np.zeros(len(df))
        s_open = np.zeros(len(df))
        
        curr_h, curr_l, curr_o = 0.0, 0.0, 0.0
        
        for i in range(len(df)):
            if is_new_day[i]:
                curr_h, curr_l, curr_o = df['High'].iloc[i], df['Low'].iloc[i], df['Open'].iloc[i]
            else:
                curr_h = max(df['High'].iloc[i], curr_h)
                curr_l = min(df['Low'].iloc[i], curr_l)
            s_high[i], s_low[i], s_open[i] = curr_h, curr_l, curr_o

        # Equilibrium vs Force Trend
        line1 = (s_open + s_high + s_low) / 3
        line2 = (s_open + s_high + s_low + df['Close'].values) / 4
        is_bull_trend = line2 > line1
        is_bear_trend = line2 < line1

        # ==========================================
        # 3. P-MASTER DOTS & V2 TAXATION (Sync with Pine)
        # ==========================================
        df['ohlc4'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        df['p_price'] = ((df['Close'] + (df['Close'] + df['Close'].shift(1).fillna(df['Close']))/2 + 
                         (df['Close'] + df['Open'])/2 + df['ohlc4']) / 4).round(4)
        
        p_change_vals = df['p_price'].diff().fillna(0).values
        green_counts = np.zeros(len(df))
        red_counts = np.zeros(len(df))
        
        g, r = 0, 0
        for i in range(len(df)):
            change = p_change_vals[i]
            if change >= 0:
                g += 1
                if r == 1: r, g = 0, max(0, g - 2)
                elif r > 1: r = 0
            else:
                r += 1
                if g == 1: g, r = 0, max(0, r - 2)
                elif g > 1: g = 0
            green_counts[i], red_counts[i] = g, r

        # ==========================================
        # 4. EXIT LOGIC (Current Price Comparison)
        # ==========================================
        p0 = df['p_price'].iloc[-1]
        p1 = df['p_price'].iloc[-2]
        exit_sig = "BULL" if p0 > p1 else "BEAR"

        # ==========================================
        # 5. ENTRY LOGIC & TIME LOCK
        # ==========================================
        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(ist).time()
        
        idx = -1
        # Flip Detection using history reference [1]
        flippedGreen = (p_change_vals[idx] >= 0) and (p_change_vals[idx-1] < 0)
        flippedRed = (p_change_vals[idx] < 0) and (p_change_vals[idx-1] >= 0)
        
        # prevCount logic (value before the current update)
        pR = red_counts[idx-1]
        pG = green_counts[idx-1]
        
        if VERBOSE:
            trend_side = "BULL SIDE" if is_bull_trend[idx] else "BEAR SIDE"
            print(f"\n--- {datetime.now(ist).strftime('%H:%M:%S')} ---")
            print(f"TREND: {trend_side} | L1: {line1[idx]:.2f} L2: {line2[idx]:.2f}")
            print(f"DOTS: P0: {p0:.4f} | Counts: R:{pR} G:{pG}")
            print(f"FLIP: Green:{flippedGreen} Red:{flippedRed}")

        entry = "NONE"
        
        # Morning Rule Check
        if now_ist < dt_time(9, 17):
            entry = "MORNING"
            if VERBOSE: print("STATUS: Waiting for 09:17 AM...")
        else:
            # Sync with Pine signals: TB, TS, CB, CS
            if is_bull_trend[idx] and 3 <= pR < 7 and flippedGreen:
                entry = "OTMBUY"   # Pine: TB
            elif is_bear_trend[idx] and 3 <= pG < 7 and flippedRed:
                entry = "OTMSELL"  # Pine: TS
            elif is_bear_trend[idx] and pR >= 7 and flippedGreen:
                entry = "ATMBUY"   # Pine: CB
            elif is_bull_trend[idx] and pG >= 7 and flippedRed:
                entry = "ATMSELL"  # Pine: CS
            else:
                entry = exit_sig
                if VERBOSE: print(f"ACTION: Holding Trend ({entry})")

        return entry, exit_sig

    except Exception as e:
        if VERBOSE: print(f"[CRITICAL ERROR] {e}")
        return "NONE", "NONE"

# Test run
if __name__ == "__main__":
    e, x = get_entry_signal()
    print(f"\nFINAL RESULT -> Entry: {e} | Exit: {x}")




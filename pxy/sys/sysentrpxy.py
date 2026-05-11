import yfinance as yf
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, time as dt_time

def get_entry_signal(df=None):
    """
    V5 Logic with V2 Taxation. 
    Synced for RUNNING BARS with 9:17 AM Morning Rule.
    """
    try:
        # 1. TIME CHECK (Morning Rule)
        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(ist).time()
        
        if now_ist < dt_time(9, 17):
            return "MORNING", "NONE"

        # 2. FETCH DATA
        if df is None:
            df = yf.download("^NSEI", period='2d', interval='1m', progress=False)
        
        if df is None or df.empty or len(df) < 20:
            return "NONE", "NONE"

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.copy()

        # ==========================================
        # 3. SESSION DATA (Zero Lag Trend)
        # ==========================================
        df.index = pd.to_datetime(df.index)
        is_new_day = df.index.date != np.roll(df.index.date, 1)
        
        s_high, s_low, s_open = np.zeros(len(df)), np.zeros(len(df)), np.zeros(len(df))
        curr_h, curr_l, curr_o = 0.0, 0.0, 0.0
        
        for i in range(len(df)):
            if is_new_day[i]:
                curr_h, curr_l, curr_o = df['High'].iloc[i], df['Low'].iloc[i], df['Open'].iloc[i]
            else:
                curr_h = max(df['High'].iloc[i], curr_h)
                curr_l = min(df['Low'].iloc[i], curr_l)
            s_high[i], s_low[i], s_open[i] = curr_h, curr_l, curr_o

        line1 = (s_open + s_high + s_low) / 3
        line2 = (s_open + s_high + s_low + df['Close'].values) / 4
        is_bull_trend = line2 > line1
        is_bear_trend = line2 < line1

        # ==========================================
        # 4. P-MASTER & V2 TAXATION
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
        # 5. EXIT LOGIC (Original Code)
        # ==========================================
        p0 = df['p_price'].iloc[-1]
        p1 = df['p_price'].iloc[-2]
        exit_sig = "BULL" if p0 > p1 else "BEAR"

        # ==========================================
        # 6. ENTRY LOGIC (Synced Action)
        # ==========================================
        idx = -1
        flippedGreen = (p_change_vals[idx] >= 0) and (p_change_vals[idx-1] < 0)
        flippedRed = (p_change_vals[idx] < 0) and (p_change_vals[idx-1] >= 0)
        
        pR = red_counts[idx-1]
        pG = green_counts[idx-1]
        
        entry = "NONE"
        if is_bull_trend[idx] and 3 <= pR < 7 and flippedGreen:
            entry = "OTMBUY"
        elif is_bear_trend[idx] and 3 <= pG < 7 and flippedRed:
            entry = "OTMSELL"
        elif is_bear_trend[idx] and pR >= 7 and flippedGreen:
            entry = "ATMBUY"
        elif is_bull_trend[idx] and pG >= 7 and flippedRed:
            entry = "ATMSELL"
        else:
            entry = exit_sig

        return entry, exit_sig

    except Exception:
        return "NONE", "NONE"



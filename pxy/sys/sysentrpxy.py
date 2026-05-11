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

        # 1. FETCH DATA - 7d period is required on Mondays to bridge the weekend
        if df is None:
            # interval='1m' is limited to the last 7 days of history
            df = yf.download("^NSEI", period='7d', interval='1m', progress=False)
        
        # Threshold: We need at least 2 bars for exit_sig (p0 vs p1). 
        # Session trend is more stable with 15+ bars.
        if df is None or df.empty or len(df) < 2:
            if VERBOSE: print(f"[DEBUG] Critical Data Failure. Bars: {len(df) if df is not None else 0}")
            return "NONE", "NONE"

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.copy()

        # ==========================================
        # 2. SESSION DATA (Zero Lag Trend)
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

        # ==========================================
        # 3. P-MASTER DOTS & V2 TAXATION
        # ==========================================
        df['ohlc4'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        df['p_price'] = ((df['Close'] + (df['Close'] + df['Close'].shift(1).fillna(df['Close']))/2 + 
                         (df['Close'] + df['Open'])/2 + df['ohlc4']) / 4).round(4)
        
        p_change = df['p_price'].diff().fillna(0).values
        g_counts, r_counts = np.zeros(len(df)), np.zeros(len(df))
        
        g, r = 0, 0
        for i in range(len(df)):
            if p_change[i] >= 0:
                g += 1
                if r == 1: r, g = 0, max(0, g - 2)
                elif r > 1: r = 0
            else:
                r += 1
                if g == 1: g, r = 0, max(0, r - 2)
                elif g > 1: g = 0
            g_counts[i], r_counts[i] = g, r

        # ==========================================
        # 4. EXIT & ENTRY LOGIC
        # ==========================================
        p0, p1 = df['p_price'].iloc[-1], df['p_price'].iloc[-2]
        exit_sig = "BULL" if p0 > p1 else "BEAR"

        idx = -1
        fG = (p_change[idx] >= 0) and (p_change[idx-1] < 0)
        fR = (p_change[idx] < 0) and (p_change[idx-1] >= 0)
        pR, pG = r_counts[idx-1], g_counts[idx-1]
        
        if VERBOSE:
            bias = "S-B" if is_bull_trend[idx] else "S-S"
            print(f"[{datetime.now(ist).strftime('%H:%M:%S')}] Bars: {len(df)} | Bias: {bias} | R:{int(pR)} G:{int(pG)} | P0:{p0:.2f}")

        # Morning Rule: Force MORNING for Entry but keep Exit valid
        if now_ist < dt_time(9, 17):
            entry = "MORNING"
        else:
            if is_bull_trend[idx] and 3 <= pR < 7 and fG: entry = "OTMBUY"
            elif not is_bull_trend[idx] and 3 <= pG < 7 and fR: entry = "OTMSELL"
            elif not is_bull_trend[idx] and pR >= 7 and fG: entry = "ATMBUY"
            elif is_bull_trend[idx] and pG >= 7 and fR: entry = "ATMSELL"
            else: entry = exit_sig

        return entry, exit_sig

    except Exception as e:
        if VERBOSE: print(f"[CRITICAL] {e}")
        return "NONE", "NONE"


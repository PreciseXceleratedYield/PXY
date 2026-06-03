# sysstrndpxy.py
import numpy as np
import pandas as pd

# Global Config 
DEBUG_MODE = True 
MA_TYPE = "TSMA"  
CHECK_CONFIRMED_ONLY = False  # ⚡ Set to False to actively process and trade the LIVE running candle

def get_signal(df: pd.DataFrame) -> tuple:
    """
    PXY Strategy Module.
    Calculates Mode 5 data and Intraday Resetting Engine lines directly inside Python.
    Handles the LIVE running candle dynamically by computing real-time indicators on row n-1.
    """
    if df is None or len(df) < 5:
        return "NONE", "NONE"

    try:
        # 1. ISOLATED MODE 5 MATRIX GENERATOR (COMPOSITE BLEND)
        df = df.copy()
        
        # Parse Dates/Timestamps to detect session changes
        if isinstance(df.index, pd.DatetimeIndex):
            timestamps = df.index
        else:
            timestamps = pd.to_datetime(df['Timestamp'] if 'Timestamp' in df.columns else df.index)
        dates = timestamps.date

        n = len(df)
        ha_o = np.zeros(n)
        
        raw_open  = df['Open'].to_numpy()
        raw_high  = df['High'].to_numpy()
        raw_low   = df['Low'].to_numpy()
        raw_close = df['Close'].to_numpy()

        # Heikin-Ashi calculation loops with intraday morning resets
        for i in range(n):
            ha_c_i = (raw_open[i] + raw_high[i] + raw_low[i] + raw_close[i]) / 4.0
            if i == 0 or dates[i] != dates[i-1]:
                ha_o[i] = (raw_open[i] + raw_close[i]) / 2.0
            else:
                ha_o[i] = (ha_o[i-1] + ha_c_i) / 2.0

        ha_c = (raw_open + raw_high + raw_low + raw_close) / 4.0
        ha_h = np.maximum(raw_high, np.maximum(ha_o, ha_c))
        ha_l = np.minimum(raw_low, np.maximum(ha_o, ha_c))

        oc2 = (raw_open + raw_close) / 2.0
        
        raw_c1 = np.empty(n)
        raw_c1[0] = raw_close[0]
        raw_c1[1:] = raw_close[:-1]

        # Mode 5 Transformed Candlestick Outputs
        src_o = (raw_open + ha_o + oc2 + raw_c1) / 4.0
        src_h = (raw_high + ha_h + oc2 + raw_close) / 4.0
        src_l = (raw_low + ha_l + oc2 + raw_c1) / 4.0
        src_c = (raw_close + ha_c + oc2 + raw_close) / 4.0

        # 2. DYNAMIC INTRADAY SESSION ENGINE MATH LOUPOUT
        sma_line   = np.zeros(n)
        tsma_line  = np.zeros(n)
        hh_session = np.zeros(n)
        ll_session = np.zeros(n)
        bar_count_session = np.zeros(n, dtype=int)

        current_count = 0
        sum_y = 0.0
        sum_x = 0.0
        sum_xx = 0.0
        sum_xy = 0.0
        curr_hh = np.nan
        curr_ll = np.nan

        for i in range(n):
            if i == 0 or dates[i] != dates[i-1]:
                current_count = 1
                sum_y  = src_c[i]
                sum_x  = 0.0
                sum_xx = 0.0
                sum_xy = 0.0
                curr_hh = src_h[i]
                curr_ll = src_l[i]
            else:
                current_count += 1
                idx = current_count - 1
                sum_y  += src_c[i]
                sum_x  += idx
                sum_xx += idx ** 2
                sum_xy += idx * src_c[i]
                curr_hh = max(curr_hh, src_h[i])
                curr_ll = min(curr_ll, src_l[i])

            bar_count_session[i] = current_count
            hh_session[i] = curr_hh
            ll_session[i] = curr_ll

            # Intraday Resetting SMA
            sma_line[i] = sum_y / current_count

            # Intraday Resetting Linear Regression Line Endpoints (TSMA)
            tsma_line[i] = src_c[i]
            if current_count > 1:
                num = (current_count * sum_xy) - (sum_x * sum_y)
                denom = (current_count * sum_xx) - (sum_x ** 2)
                if denom != 0:
                    slope = num / denom
                    current_idx = current_count - 1
                    intercept = (sum_y - (slope * sum_x)) / current_count
                    tsma_line[i] = (slope * current_idx) + intercept

        base_ma_line = sma_line if MA_TYPE.upper() == "SMA" else tsma_line

        # Core Structural Boundaries Matching Pine Mathematically
        pxy_st_line  = (base_ma_line + hh_session + ll_session + src_c) / 4.0
        pxy_st_no_ll = (base_ma_line + hh_session + src_c) / 3.0
        pxy_st_no_hh = (base_ma_line + ll_session + src_c) / 3.0

        # 3. APPLY DYNAMIC LOOKUPS DIRECTLY MATCHING PINE ROUTING SWITCH
        if CHECK_CONFIRMED_ONLY:
            # 🔒 Confirmed Non-Reprinting: Past 2 vs Past 1
            c0_idx, c1_idx = n - 2, n - 3
        else:
            # ⚡ Live Fast Track: Past 1 vs Live Running Candle (Row n-1 handles real-time ticks)
            c0_idx, c1_idx = n - 1, n - 2

        # Map dynamic lookups precisely to variable positions
        c0 = src_c[c0_idx]
        c1 = src_c[c1_idx]
        
        st0 = pxy_st_line[c0_idx]
        st1 = pxy_st_line[c1_idx]
        
        no_ll0 = pxy_st_no_ll[c0_idx]
        no_ll1 = pxy_st_no_ll[c1_idx]
        
        no_hh0 = pxy_st_no_hh[c0_idx]
        no_hh1 = pxy_st_no_hh[c1_idx]

        entry, exit_sig = "NONE", "NONE"
        min_bars_required = 3 if CHECK_CONFIRMED_ONLY else 2

        # 4. EXPLICIT PRIORITY SIGNAL SORTING MATRIX
        if bar_count_session[c0_idx] >= min_bars_required:
            cross_buy  = (c0 > st0) and (c1 <= st1)
            cross_sell = (c0 < st0) and (c1 >= st1)
            
            force_buy  = (c0 > no_ll0) and (c1 <= no_ll1)
            force_sell = (c0 < no_hh0) and (c1 >= no_hh1)

            if force_buy:
                entry, exit_sig = "FORCESELL", "FORCESELL"  
            elif force_sell:
                entry, exit_sig = "FORCEBUY", "FORCEBUY"    
            elif cross_buy:
                entry, exit_sig = "CROSSBUY", "CROSSBUY"    
            elif cross_sell:
                entry, exit_sig = "CROSSSELL", "CROSSSELL"  

        if DEBUG_MODE:
            print(f"\n--- PXY RUNNING CANDLE ENGINE SYNC ---")
            print(f"Engine Switch State  -> CHECK_CONFIRMED_ONLY = {CHECK_CONFIRMED_ONLY}")
            print(f"Target Row (Index 0) -> Index: {c0_idx} | Session Bars: {bar_count_session[c0_idx]}")
            print(f"Prior Row  (Index 1) -> Index: {c1_idx} | Session Bars: {bar_count_session[c1_idx]}")
            print(f"Live Price Vector    -> C0 (Running): {c0:.2f} | C1 (Completed): {c1:.2f}")
            print(f"Live Channels Vector -> ST0: {st0:.2f} | Upper Band: {no_ll0:.2f} | Lower Band: {no_hh0:.2f}")
            print(f"Calculated Engine Output -> {entry}\n")

        return entry, exit_sig

    except Exception as e:
        if DEBUG_MODE:
            print(f"PXY Master Translation Engine Exception: {e}")
        return "NONE", "NONE"


# --- STANDALONE TESTING MODULE ---
if __name__ == "__main__":
    from sysdthapxy import get_pxy_data
    
    print("\n[PXY STRND ENGINE] Standalone Live Stream Listener Initiated.")
    print("--------------------------------------------------")
    
    try:
        print("Polling latest day-specific data from sysdthapxy...")
        _, _, _, live_df = get_pxy_data(df=None)
        
        if live_df is not None and not live_df.empty:
            print(f"Data Successfully Retrieved. Array length: {len(live_df)} entries.")
            entry_sig, exit_sig = get_signal(live_df)
            
            print("==================================================")
            print(f"⚡ LIVE STREAM OUTPUT -> Entry: {entry_sig} | Exit: {exit_sig}")
            print("==================================================\n")
        else:
            print("❌ Error: Upstream module returned an empty or invalid DataFrame frame.")
            
    except Exception as e:
        print(f"❌ Critical Connection Exception Hit: {e}")


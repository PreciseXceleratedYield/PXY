def get_entry_signal(df=None):
    try:
        # 1. FETCH DATA (Fetch first so we have prices for the exit comparison)
        if df is None:
            df = yf.download("^NSEI", period='2d', interval='1m', progress=False)
        
        if df is None or df.empty or len(df) < 20:
            return "NONE", "NONE"

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.copy()

        # [ ... Session Data & Taxation Logic remains exactly same ... ]
        # (Assuming the logic for line1, line2, p_price, and counts is here)

        # ==========================================
        # 3. EXIT LOGIC (Always Calculates)
        # ==========================================
        p0 = df['p_price'].iloc[-1]
        p1 = df['p_price'].iloc[-2]
        exit_sig = "BULL" if p0 > p1 else "BEAR"

        # ==========================================
        # 4. ENTRY LOGIC with Morning Rule
        # ==========================================
        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(ist).time()

        # Morning Rule: Only overrides the 'entry' part
        if now_ist < dt_time(9, 17):
            entry = "MORNING"
        else:
            idx = -1
            flippedGreen = (p_change_vals[idx] >= 0) and (p_change_vals[idx-1] < 0)
            flippedRed = (p_change_vals[idx] < 0) and (p_change_vals[idx-1] >= 0)
            pR, pG = red_counts[idx-1], green_counts[idx-1]
            
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

        return entry, exit_sig # Now exit_sig is never forced to "NONE"

    except Exception:
        return "NONE", "NONE"


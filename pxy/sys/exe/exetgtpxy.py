# sys/exe/exetgtpxy.py
import math

def target_price(row):
    """
    3-PHASE AIRTIGHT OPTION TARGET (Premium Based):
    PHASE 1: Initial Entry (Depth <= 2) -> max(10, ATR * Power)
    PHASE 2: Deep Trend (Depth > 2 + Aligned) -> ATR * Power * Depth
    PHASE 3: Reversal (Mullu/Signal Flip) -> Fixed 10 Points
    
    NOTE: Both CE and PE ADD points because Option Price must go UP for profit.
    Baseline: pxy_entry (Recalculated every minute with 0.20 decay).
    """
    try:
        # 1. BASELINE: Use the decaying dynamic pxy_entry from OMS
        entry_prc = float(row.get("pxy_entry", row.get("buy_prc", 0)))
        symbol = str(row.get("symbol", "")).upper()
        
        if entry_prc <= 0: 
            return 0

        # 2. EXTRACT DATA FROM THE OMS ROW (Synced from market_snapshot)
        atr = float(row.get("atr", 20))
        ce_p = float(row.get("ce_power", 1.0))
        pe_p = float(row.get("pe_power", 1.0))
        mullu = str(row.get("direction", "SIDE")).upper() # UP or DOWN
        signal = str(row.get("entry", "NONE")).upper()
        
        # 3. ALIGNMENT & PHASE SELECTION
        if "CE" in symbol:
            power = ce_p
            depth = int(row.get("hkin_ce_depth", 0))
            # Aligned if Mullu is UP and Signal is BUY
            is_aligned = (mullu == "UP") and ("BUY" in signal)
        elif "PE" in symbol:
            power = pe_p
            depth = int(row.get("hkin_pe_depth", 0))
            # Aligned if Mullu is DOWN and Signal is SELL
            is_aligned = (mullu == "DOWN") and ("SELL" in signal)
        else:
            return entry_prc

        # 4. CALCULATE THE TARGET "PUSH" (POINTS)
        # --- PHASE 3: EMERGENCY / REVERSAL ---
        if not is_aligned:
            # Mullu has flipped against the position. 
            # Ask for only 10 points to escape the trade fast.
            total_points = 10.0

        # --- PHASE 2: DEEP TREND ACCELERATION ---
        elif depth > 2:
            # Strong conviction trend (HKIN Depth 3, 4, 5).
            # Target = ATR * Power * Depth (Capped at 5 depth)
            total_points = atr * power * min(depth, 5)

        # --- PHASE 1: INITIAL TARGET ---
        else:
            # Early entry or normal trend. 
            # Target = max(10.0, ATR * Power)
            total_points = max(10.0, atr * power)

        # 5. FINAL CALCULATION
        # Both CE/PE: Current Decaying Price + Target Points
        # As pxy_entry drops 0.20/min, this Target also "melts" toward the market.
        target = entry_prc + total_points

        return round(target, 2)

    except Exception:
        # Final safety fallback: 10 points above current dynamic price
        return round(float(row.get("pxy_entry", 0)) + 10, 2)


        return round(target, 2)

    except Exception:
        # Final safety fallback: 10 points above current dynamic price
        return round(float(row.get("pxy_dynamic_buy", 0)) + 10, 2)

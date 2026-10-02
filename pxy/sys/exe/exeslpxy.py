# sys/exe/exeslpxy.py

from syscnfgpxy import EXESLPXY_FIXED_SL_BUFFER, EXESLPXY_MIN_PRICE


def stop_loss(row):
    """
    Stop-loss calculation based on OPTION PREMIUM:
    SL = pxy_entry - 10 points (FIXED_SL_BUFFER)
    
    NOTE: Both CE and PE SUBTRACT the buffer because we exit 
    when the OPTION PRICE drops below our risk threshold.
    """
    try:
        # 1. BASELINE: The decaying dynamic option premium
        # Anchored to pxy_entry which melts 0.20 per minute
        entry = float(row.get("pxy_entry", row.get("buy_prc", 0)))
        symbol = str(row.get("symbol", "")).upper()

        if entry <= 0:
            return 0

        # 2. CALCULATION:
        # In Options, profit is UP (+), loss is DOWN (-).
        # As pxy_entry drops 0.20/min, the Stop Loss also "slides" down.
        sl_price = entry - EXESLPXY_FIXED_SL_BUFFER

        # 3. FLOOR: Ensure SL doesn't go below a "Trash" value (e.g., 2.0)
        # This keeps the order valid for the exchange at all times.
        return round(max(sl_price, EXESLPXY_MIN_PRICE), 2)

    except Exception:
        # Fallback: 10 points below original buy price
        return round(float(row.get("buy_prc", 0)) - EXESLPXY_FIXED_SL_BUFFER, 2)

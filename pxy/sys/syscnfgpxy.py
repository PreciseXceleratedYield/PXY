"""
Executes exactly 6 structural, isolated OHLC mathematical transformations:
Mode 0: Hyper-Sensitive Modified Close Candles (Green Close=(High+Close)/2, Red Close=(Low+Close)/2)
Mode 1: Raw Candles
Mode 2: Mid-Body (OC/2) Pure Math Candles
Mode 3: Full Range (OHLC/4) Pure Math Candles
Mode 4: Standard Heikin-Ashi Candles
Mode 5: Master Ensemble Average of Modes 0, 1, 2, 3, and 4 (Divided by 5)
"""

from datetime import datetime
import pytz

# ---------------- DYNAMIC TIME-BASED TICKER EVALUATION ----------------
def resolve_active_ticker():
    """
    Evaluates current time in Asia/Kolkata timezone.
    Returns:
        str: Exact Yahoo Finance symbol string.
        - 00:00 to 15:45 IST -> Nifty (^NSEI)
        - 15:45 to 24:00 IST -> WTI Crude Oil Mini Proxy (MCL=F)
    """
    tz = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(tz)
    
    # Calculate current absolute minutes since midnight
    current_minutes = (now_ist.hour * 60) + now_ist.minute
    cutoff_minutes = (15 * 60) + 45  # 15:45 (3:45 PM) is 945 minutes
    
    if current_minutes < cutoff_minutes:
        return "^NSEI"
    else:
        return "CL=F"

# ---------------- LOCAL SYSTEM CONFIGURATION ----------------
PARAMS = {
    "ticker": resolve_active_ticker(),  # Single value assigned directly
    "ohlc_mode": 2                      # Switch Modes here (0 through 5)
}

# ---------------- CONSTANTS DERIVED FROM CONFIG ----------------
TICKER = PARAMS["ticker"]
OHLC_MODE = PARAMS["ohlc_mode"]
TIMEZONE = pytz.timezone("Asia/Kolkata")

# ---------------- SYSTEM SELF TEST ----------------
if __name__ == "__main__":
    print("=== CONFIGURATION FILE VERIFICATION ===")
    print(f"CURRENT SYSTEM TIME (IST): {datetime.now(TIMEZONE).strftime('%H:%M:%S')}")
    print(f"TARGET TICKER            : {TICKER}")
    print(f"ACTIVE MODE              : {OHLC_MODE}")
    print(f"SYSTEM TIMEZONE          : {TIMEZONE}")


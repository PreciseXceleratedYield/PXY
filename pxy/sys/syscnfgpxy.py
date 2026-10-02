# syscnfgpxy.py
"""
Executes exactly 6 structural, isolated OHLC mathematical transformations:
Mode 0: Hyper-Sensitive Modified Close Candles (Green Close=(High+Close)/2, Red Close=(Low+Close)/2)
Mode 1: Raw Candles
Mode 2: Mid-Body (OC/2) Pure Math Candles
Mode 3: Full Range (OHLC/4) Pure Math Candles
Mode 4: Standard Heikin-Ashi Candles
Mode 5: Master Ensemble Average of Modes 0, 1, 2, 3, and 4 (Divided by 5)
"""


import pytz

# ---------------- LOCAL SYSTEM CONFIGURATION ----------------
PARAMS = {
    "ticker": "BTC-USD",          # Nifty 50 index
}

# ---------------- CONSTANTS DERIVED FROM CONFIG ----------------
TICKER = PARAMS["ticker"]
TIMEZONE = pytz.timezone("Asia/Kolkata")

# ---------------- SYSTEM SELF TEST ----------------
if __name__ == "__main__":
    print("=== CONFIGURATION FILE VERIFICATION ===")
    print(f"TARGET TICKER  : {TICKER}")
    print(f"SYSTEM TIMEZONE: {TIMEZONE}")

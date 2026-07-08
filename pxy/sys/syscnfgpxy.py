# syscnfgpxy.py
import pytz

"""
================================================================================
                    CORE ENGINE DATA TRANSFORMATION MODES
================================================================================
MODE 0: Line-Bar Conversion Matrix
        - Open = High = Low = Close: Raw Close (C_t)
        - Use Case: Strip out all vertical height to run pure close-line logic.

MODE 1: Raw Baseline (Unaltered)
        - Open / High / Low / Close: Direct, unmodified yFinance exchange data.
        - Use Case: Clean benchmarking and true raw execution prices.

MODE 2: Recursive Standard Heikin-Ashi Matrix
        - Close: (Open + High + Low + Close) / 4.0
        - Open:  Recursive average of previous HA Open and previous HA Close.
        - High:  Maximum of (Raw High, HA Open, HA Close).
        - Low:   Minimum of (Raw Low, HA Open, HA Close).
        - Use Case: Seamless gapless candle sequences that smooth out market noise.

MODE 3: OC/2 Mid-Body Matrix
        - Open = High = Low = Close: (Open + Close) / 2.0
        - Use Case: Compress bar ranges into strict body midpoint tracking channels.

MODE 4: Blended Average Ensemble (ACTIVE DEFAULT)
        - Evaluates a respective ensemble average of [Mode 0 + Mode 1 + Mode 2 + Mode 3] / 4.0
        - Use Case: Deep structural smoothing that neutralizes single-model mathematical anomalies.
================================================================================
"""

# ---------------- LOCAL SYSTEM CONFIGURATION ----------------
PARAMS = {
    "ticker": "BTC-USD",          # Options: "^NSEI", "^NSEBANK", "BTC-USD", "GC=F", "GBPUSD=X", "^GSPC"
    "ohlc_mode": 4               # Switch Modes here (0 through 4)
}

# ---------------- CONSTANTS DERIVED FROM CONFIG ----------------
TICKER = PARAMS["ticker"]
OHLC_MODE = PARAMS["ohlc_mode"]
TIMEZONE = pytz.timezone("Asia/Kolkata")

# ---------------- SYSTEM SELF TEST ----------------
if __name__ == "__main__":
    print("=== CONFIGURATION FILE VERIFICATION ===")
    print(f"TARGET TICKER  : {TICKER}")
    print(f"ACTIVE MODE    : {OHLC_MODE}")
    print(f"SYSTEM TIMEZONE: {TIMEZONE}")


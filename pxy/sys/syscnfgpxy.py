# syscnfgpxy.py
import pytz

"""
================================================================================
                    CORE ENGINE DATA TRANSFORMATION MODES
================================================================================
MODE 0: Flipped Geometry Matrix
        - Open: 1/4 of previous range if Bullish; 3/4 if Bearish.
        - High: Raw High (forced up to previous close if Bearish).
        - Low:  Raw Low (forced down to previous close if Bullish).
        - Close: Standard raw close.
        - Use Case: Boundary breakouts and asymmetric trailing stops.

MODE 1: Raw Baseline (Unaltered)
        - Open / High / Low / Close: Direct, unmodified yFinance exchange data.
        - Use Case: Clean benchmarking and true raw execution prices.

MODE 2: Simplified Heikin-Ashi (Non-Recursive)
        - Close: (Open + High + Low + Close) / 4.0
        - Open:  (Open + Close) / 2.0
        - High / Low: Kept completely at raw chart levels.
        - Use Case: Smooth price tracking without multi-bar historical lag.

MODE 3: Open-Close Median Flatline
        - Open = High = Low = Close: (Open + Close) / 2.0
        - Use Case: Compress bar ranges into strict midpoint tracking channels.

MODE 4: Shift Momentum Blocks
        - Open / Low:  Previous bar Close (C_t-1).
        - High / Close: Current bar Close (C_t).
        - Use Case: Pure vector momentum that ignores standard bar structures.

MODE 5: Composite Blended Average
        - Evaluates an ensemble average of [Raw + Mode 2 + Mode 3 + Mode 4] / 4
        - Use Case: Structural smoothing that neutralizes single-model errors.

MODE 6: Rolling 4-SMA OC/2 Matrix
        - Close: 4-period SMA of the Open-Close median midpoint.
        - Open:  Recursive calculation from previous transformed coordinates.
        - Use Case: Eliminating market noise during tight consolidations.

MODE 7: Recursive OHLC/4 Candle Framework (ACTIVE DEFAULT)
        - Close: (Open + High + Low + Close) / 4.0
        - Open:  Previous bar's transformed Close value.
        - High:  Maximum of (Raw High, Transformed Open, Transformed Close).
        - Low:   Minimum of (Raw Low, Transformed Open, Transformed Close).
        - Use Case: Seamless gapless candle sequences; builds custom SMA/ST loops.
================================================================================
"""

# ---------------- LOCAL SYSTEM CONFIGURATION ----------------
PARAMS = {
    "ticker": "BTC-USD",          # Options: "^NSEI", "^NSEBANK", "BTC-USD", "GC=F", "GBPUSD=X", "^GSPC"
    "ohlc_mode": 7                # Switch Modes here (0 through 7)
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


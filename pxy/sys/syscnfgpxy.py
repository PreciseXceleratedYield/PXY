# syscnfgpxy.py
import pytz

# ---------------- LOCAL SYSTEM CONFIGURATION ----------------
PARAMS = {
    "ticker": "^NSEI",          # Options: "^NSEI", "^NSEBANK", "BTC-USD", "GC=F", "GBPUSD=X", "^GSPC"
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

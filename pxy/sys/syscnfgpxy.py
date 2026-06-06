import pytz

# ---------------- LOCAL SYSTEM CONFIGURATION ----------------
PARAMS = {
    "ticker": "BTC-USD",          # Options: "^NSEI", "^NSEBANK", "BTC-USD", "GC=F", "GBPUSD=X"^GSPC
    "ohlc_mode": 1           # Change Mode Here: 1=Raw, 2=HA, 3=oc/2, 4=c1c0, 5=Composite Average
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


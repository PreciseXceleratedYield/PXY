import pytz

# ---------------- SINGLE CONFIG ----------------
PARAMS = {
    "ticker": "^GSPC",          # or "^NSEI""^NSEBANK" BTC-USD COMEX:GC1! GBP/USD Yahoo: GBPUSD=X TradingView: FX:GBPUSD
    "supertrend_period": 7,
    "supertrend_multiplier": 7
}

# ---------------- CONSTANTS ----------------
TICKER = PARAMS["ticker"]

TIMEZONE = pytz.timezone("Asia/Kolkata")

# ---------------- SELF TEST ----------------
if __name__ == "__main__":
    print("PARAMS:", PARAMS)
    print("TICKER:", TICKER)

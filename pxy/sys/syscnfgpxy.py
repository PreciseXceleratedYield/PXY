import pytz

# ---------------- SINGLE CONFIG ----------------
PARAMS = {
    "ticker": "AAPL",          # or "^NSEI""^NSEBANK" BTC-USD COMEX:GC1!
    "supertrend_period": 3,
    "supertrend_multiplier": 3
}

# ---------------- CONSTANTS ----------------
TICKER = PARAMS["ticker"]

TIMEZONE = pytz.timezone("Asia/Kolkata")

# ---------------- SELF TEST ----------------
if __name__ == "__main__":
    print("PARAMS:", PARAMS)
    print("TICKER:", TICKER)

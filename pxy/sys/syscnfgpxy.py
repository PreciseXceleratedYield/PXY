import pytz

# ---------------- SINGLE CONFIG ----------------
PARAMS = {
    "ticker": "^NSEI",  # options: "^NSEI", "^NSEBANK", "BTC-USD", "GC=F", "GBPUSD=X"
    "supertrend_period": 2,
    "supertrend_multiplier": 1
}

# ---------------- CONSTANTS ----------------
TICKER = PARAMS["ticker"]

TIMEZONE = pytz.timezone("Asia/Kolkata")

# ---------------- SELF TEST ----------------
if __name__ == "__main__":
    print("PARAMS:", PARAMS)
    print("TICKER:", TICKER)

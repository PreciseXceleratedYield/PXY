import pytz

# ---------------- SINGLE CONFIG ----------------
PARAMS = {
    "ticker": "^FTSE" #"^NSEBANK",          # or "^NSEI"
    "supertrend_period": 2,
    "supertrend_multiplier": 2
}

# ---------------- CONSTANTS ----------------
TICKER = PARAMS["ticker"]

TIMEZONE = pytz.timezone("Asia/Kolkata")

# ---------------- SELF TEST ----------------
if __name__ == "__main__":
    print("PARAMS:", PARAMS)
    print("TICKER:", TICKER)


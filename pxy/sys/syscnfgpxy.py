# syscnfgpxy.py

import pytz

# Minimal config for all imports to work
PARAMS = {
    "ticker": "^NSEI"  # NIFTY 50  # old scripts using PARAMS["ticker"]
}

# TICKER constant for scripts that import TICKER directly
TICKER = PARAMS["ticker"]

# Optional timezone
TIMEZONE = pytz.timezone("Asia/Kolkata")

# syscnfgpxy.py

# Minimal config for all scripts
PARAMS = {
    "ticker": "^NSEI",              # default ticker
    "supertrend_period": 2,         # required by syssuperpxy.py
    "supertrend_multiplier": 2      # required by syssuperpxy.py
}

# Optional: a TICKER constant for scripts importing TICKER directly
TICKER = PARAMS["ticker"]

# -------- Self-test --------
if __name__ == "__main__":
    print("PARAMS:", PARAMS)
    print("TICKER:", TICKER)



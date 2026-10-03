# sysvixpxy.py

import yfinance as yf
from colorama import Fore, Style, init
from syscnfgpxy import RUNMODE

init(autoreset=True)


# ----------------------------
# Get latest India VIX
# ----------------------------
def get_vix_flag():
    try:
        if RUNMODE == "TST":
            return "G"
        df = yf.Ticker("^INDIAVIX").history(period="1d", interval="5m")
        if df.empty:
            return "X"
        vix = df["Close"].iloc[-1]

        # Options-friendly mapping
        if vix < 15:
            return "G"  # Calm / Sideways
        elif vix < 22:
            return "C"  # Risky / Momentum
        else:
            return "S"  # Dangerous / Momentum

    except:
        return "X"


# ----------------------------
# Get global market sentiment
# ----------------------------
def get_global_sentiment():
    try:
        if RUNMODE == "TST":
            return "M"
        indices = ["^GSPC", "^IXIC", "^N225"]
        score = 0

        for symbol in indices:
            df = yf.Ticker(symbol).history(period="1d")
            if df.empty:
                continue
            if df["Close"].iloc[-1] > df["Open"].iloc[-1]:
                score += 1
            else:
                score -= 1

        if score >= 2:
            return "B"  # Positive
        elif score <= -2:
            return "S"  # Negative
        else:
            return "M"  # Sideways

    except:
        return "X"


# ----------------------------
# Expand codes to human-readable
# ----------------------------
def expand_vix(v):
    return {
        "G": "Sideways",
        "C": "Momentum",
        "S": "Momentum",
        "X": "No Data"
    }.get(v, "Unknown")


def expand_sentiment(s):
    return {
        "B": "Positive",
        "M": "Sideways",
        "S": "Negative",
        "X": "No Data"
    }.get(s, "Unknown")


# ----------------------------
# Get both values
# ----------------------------
def get_market_context():
    vix_flag = get_vix_flag()
    sentiment = get_global_sentiment()
    return vix_flag, sentiment


# ----------------------------
# Print nicely in 42-width dashboard
# ----------------------------
def print_market_context_options():
    vix_flag, sentiment = get_market_context()

    width = 42
    left = f"VIX:{expand_vix(vix_flag)}"
    right = f"WORLD:{expand_sentiment(sentiment)}"

    print(Fore.LIGHTBLACK_EX + Style.BRIGHT + f"{left:<21}{right:>21}")


# ----------------------------
# Run standalone
# ----------------------------
if __name__ == "__main__":
    print_market_context_options()

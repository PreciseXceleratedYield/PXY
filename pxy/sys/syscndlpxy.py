# syscndlpxy.py (FIXED + UNIFIED)

from colorama import Fore, Style, init, deinit
from sysdtafpxy import fetch_yf_data

init(autoreset=True)

WIDTH = 42


# ---------------- CORE CANDLE (SOURCE OF TRUTH) ----------------
def get_latest_candle(df=None):
    if df is None or df.empty:
        df = fetch_yf_data()

    if df is None or df.empty or len(df) < 1:
        return None

    row = df.iloc[-1]

    return {
        "open": float(row["Open"]),
        "high": float(row["High"]),
        "low": float(row["Low"]),
        "close": float(row["Close"])
    }


# ---------------- DETERMINISTIC VISUAL ENGINE ----------------
def build_candle_bar(o, h, l, c, width=WIDTH):

    o, h, l, c = map(float, (o, h, l, c))

    rng = h - l
    if rng == 0:
        rng = 1e-9

    # normalize positions (0 → 1 scale)
    lower = max(0.0, min(1.0, (min(o, c) - l) / rng))
    upper = max(0.0, min(1.0, (h - max(o, c)) / rng))
    body  = max(0.0, 1.0 - lower - upper)

    # FIXED integer allocation (NO ROUNDING DRIFT)
    lower_len = int(lower * width)
    body_len  = int(body * width)
    upper_len = width - lower_len - body_len

    if body_len < 1:
        body_len = 1
        if lower_len + body_len > width:
            lower_len = width - body_len
        upper_len = width - lower_len - body_len

    bar = ""

    # lower wick
    bar += Fore.LIGHTBLACK_EX + "█" * lower_len

    # body
    if c > o:
        bar += Fore.GREEN + "█" * body_len
    elif o > c:
        bar += Fore.RED + "█" * body_len
    else:
        bar += Fore.YELLOW + "█" * body_len

    # upper wick
    bar += Fore.LIGHTBLACK_EX + "█" * upper_len

    return bar + Style.RESET_ALL


# ---------------- PUBLIC API (USE THIS EVERYWHERE) ----------------
def get_day_candle_bar(df=None):
    candle = get_latest_candle(df)

    if not candle:
        return "No candle data"

    return build_candle_bar(
        candle["open"],
        candle["high"],
        candle["low"],
        candle["close"]
    )


# ---------------- SELF TEST ----------------
if __name__ == "__main__":
    df = fetch_yf_data()
    print(get_day_candle_bar(df))
    deinit()

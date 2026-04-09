# syscndlpxy.py

from colorama import Fore, Style, init, deinit
from sysdtafpxy import fetch_yf_data

init(autoreset=True)

MAX_BAR_LENGTH = 42

def get_day_candle_bar(df=None):
    """
    Returns a 42-width colored bar for the LATEST 1-MIN candle.
    Falls back gracefully if df is empty or malformed.
    """
    try:
        if df is None or df.empty:
            df = fetch_yf_data()

        if df.empty or len(df) < 1:
            return "No candle data"

        row = df.iloc[-1]
        o, h, l, c = row['Open'], row['High'], row['Low'], row['Close']

        candle_range = h - l
        if candle_range == 0:
            candle_range = 1e-5  # prevent division by zero

        # Calculate % of wicks/body relative to range
        if c >= o:  # bullish
            lower_pct = (o - l) / candle_range
            body_pct  = (c - o) / candle_range
        else:       # bearish
            lower_pct = (c - l) / candle_range
            body_pct  = (o - c) / candle_range

        upper_pct = 1 - lower_pct - body_pct

        # Convert to lengths for the bar
        lower_len = round(lower_pct * MAX_BAR_LENGTH)
        body_len  = max(1, round(body_pct * MAX_BAR_LENGTH))
        upper_len = MAX_BAR_LENGTH - lower_len - body_len

        bar = ""
        # Lower wick
        bar += Fore.LIGHTBLACK_EX + '█' * lower_len
        # Body
        if c > o:
            bar += Fore.GREEN + '█' * body_len
        elif o > c:
            bar += Fore.RED + '█' * body_len
        else:
            bar += Fore.YELLOW + '█' * body_len
        # Upper wick
        bar += Fore.LIGHTBLACK_EX + '█' * upper_len

        return bar + Style.RESET_ALL

    except Exception as e:
        return f"Error: {e}"


# -------- Self-test --------
if __name__ == "__main__":
    df = fetch_yf_data()
    print(get_day_candle_bar(df))
    deinit()

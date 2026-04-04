# syscndlpxy.py

from colorama import Fore, Style, init, deinit
from sysdtafpxy import fetch_yf_data

init(autoreset=True)

MAX_BAR_LENGTH = 42

def get_day_candle_bar(df=None):
    """
    Returns a 42-width colored bar for the LATEST 1-MIN candle
    """
    try:
        if df is None or df.empty:
            df = fetch_yf_data()

        if df.empty or len(df) < 1:
            return "No candle data"

        # ✅ ONLY last 1-min candle
        row = df.iloc[-1]

        o = row['Open']
        h = row['High']
        l = row['Low']
        c = row['Close']

        candle_length = h - l
        if candle_length == 0:
            candle_length = 1e-5

        # Body + wicks %
        if c > o:  # bullish
            n = round(((o - l) / candle_length) * 100)
            x = round(((c - o) / candle_length) * 100)
        else:      # bearish
            n = round(((c - l) / candle_length) * 100)
            x = round(((o - c) / candle_length) * 100)

        m = 100 - n - x

        # Convert to bar length
        n_len = round((n / 100) * MAX_BAR_LENGTH)
        x_len = round((x / 100) * MAX_BAR_LENGTH)
        m_len = MAX_BAR_LENGTH - n_len - x_len

        bar = ""

        # Lower wick
        bar += Fore.LIGHTBLACK_EX + '█' * n_len

        # Body
        if c > o:
            bar += Fore.GREEN + '█' * x_len
        elif o > c:
            bar += Fore.RED + '█' * x_len
        else:
            bar += Fore.YELLOW + '█' * x_len

        # Upper wick
        bar += Fore.LIGHTBLACK_EX + '█' * m_len

        return bar + Style.RESET_ALL

    except Exception as e:
        return f"Error: {e}"


# -------- Self-test --------
if __name__ == "__main__":
    df = fetch_yf_data()
    print(get_day_candle_bar(df))
    deinit()

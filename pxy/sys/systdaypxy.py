import yfinance as yf
from colorama import Fore, Style, init, deinit
from syscnfgpxy import TICKER
import pytz
from datetime import datetime, time

init(autoreset=True)

WIDTH = 42


# ---------------- HEADER ----------------
def print_header(today_close, prev_close):
    text = "🏦 PXY® PreciseXceleratedYield Pvt Ltd🏦 "

    if prev_close is None:
        color = Fore.YELLOW
    elif today_close > prev_close:
        color = Fore.GREEN
    elif today_close < prev_close:
        color = Fore.RED
    else:
        color = Fore.YELLOW

    print(color + Style.BRIGHT + f"{text:^{WIDTH}}")


# ---------------- CANDLE ----------------
def print_candle(o, h, l, c):
    rng = h - l
    if rng == 0:
        return

    if c >= o:
        lower = (o - l) / rng
        body  = (c - o) / rng
        color = Fore.GREEN
    else:
        lower = (c - l) / rng
        body  = (o - c) / rng
        color = Fore.RED

    upper = 1 - lower - body

    lower_len = int(round(lower * WIDTH))
    body_len  = max(1, int(round(body * WIDTH)))
    upper_len = WIDTH - lower_len - body_len

    print(
        Fore.LIGHTBLACK_EX + "█" * lower_len +
        color + "█" * body_len + Style.RESET_ALL +
        Fore.LIGHTBLACK_EX + "█" * upper_len
    )

    low_str   = str(int(round(l)))
    close_str = str(int(round(c)))
    high_str  = str(int(round(h)))

    print(f"{low_str:<10}{close_str:^22}{high_str:>10}")


# ---------------- CORE FUNCTION ----------------
def get_market_snapshot(TICKER):
    result = {}

    # -------- DAILY DATA --------
    df = yf.Ticker(TICKER).history(period="2d")
    if df.empty or len(df) < 2:
        return None

    today = df.iloc[-1]
    prev = df.iloc[-2]

    o, h, l, c = today.Open, today.High, today.Low, today.Close
    prev_close = prev.Close

    result.update({
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "prev_close": prev_close
    })

    # -------- BIAS --------
    midpoint = (h + l) / 2

    if c > midpoint and c > prev_close:
        bias = "S-BULL"
    elif c > midpoint:
        bias = "W-BULL"
    elif c < midpoint and c < prev_close:
        bias = "S-BEAR"
    elif c < midpoint:
        bias = "W-BEAR"
    else:
        bias = "NEUTRAL"

    result["bias"] = bias

    # -------- POWER --------
    rng = h - l
    if rng == 0:
        power = 1
    else:
        body_position = abs(c - midpoint)
        power = int((body_position / rng) * 10)
        power = max(1, min(power, 10))

    result["power"] = power

    # -------- BREAKOUT --------
    IST = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(IST).time()

    df_1m = yf.Ticker(TICKER).history(period="1d", interval="1m")

    breakout = "NA"

    if not df_1m.empty:
        df_1m = df_1m.tz_localize(None)
        morning_df = df_1m.between_time("09:15", "09:30")

        if not morning_df.empty:
            m_high = morning_df["High"].max()
            m_low = morning_df["Low"].min()

            if time(9, 15) <= now_ist <= time(9, 30):
                if c > m_high:
                    breakout = "ACT-BULL"
                elif c < m_low:
                    breakout = "ACT-BEAR"
                else:
                    breakout = "WAIT"

    result["breakout"] = breakout

    # -------- % CALCULATIONS --------
    o_change = ((c - o) / o) * 100 if o != 0 else 0
    m_change = ((c - midpoint) / midpoint) * 100 if midpoint != 0 else 0

    result["o_change"] = round(o_change, 2)
    result["m_change"] = round(m_change, 2)

    return result


# ---------------- MAIN (PRINT ONLY) ----------------
def main():
    data = get_market_snapshot(TICKER)

    if not data:
        print("No data")
        return

    o = data["open"]
    h = data["high"]
    l = data["low"]
    c = data["close"]
    prev_close = data["prev_close"]

    # HEADER
    print_header(c, prev_close)

    # CANDLE
    print_candle(o, h, l, c)

    # -------- BIAS + POWER --------
    bias = data["bias"]
    power = data["power"]

    left_label = Fore.YELLOW + "Bias:"
    left_value = (Fore.GREEN if "BULL" in bias else Fore.RED) + bias

    right_label = Fore.YELLOW + "Power:"
    power_color = Fore.GREEN if power > 6 else Fore.RED if power < 3 else Fore.YELLOW
    right_value = power_color + str(power)

    spacing = WIDTH - len(f"Bias:{bias}") - len(f"Power:{power}")
    print(left_label + left_value + " " * spacing + right_label + right_value)

    # -------- BREAK + % --------
    breakout = data["breakout"]
    o_change = data["o_change"]
    m_change = data["m_change"]

    o_str = f"O:{o_change:+.2f}%"
    m_str = f"M:{m_change:+.2f}%"

    o_color = Fore.GREEN if o_change > 0 else Fore.RED if o_change < 0 else Fore.YELLOW
    m_color = Fore.GREEN if m_change > 0 else Fore.RED if m_change < 0 else Fore.YELLOW

    right_value = o_color + o_str + Fore.WHITE + " | " + m_color + m_str

    left_label = Fore.YELLOW + "Break:"
    left_value = (
        Fore.GREEN if "BULL" in breakout else
        Fore.RED if "BEAR" in breakout else
        Fore.YELLOW
    ) + breakout

    spacing = WIDTH - len(f"Break:{breakout}") - len(f"{o_str} | {m_str}")

    print(
        left_label + left_value +
        " " * max(1, spacing) +
        right_value
    )


# ---------------- RUN ----------------
if __name__ == "__main__":
    main()
    deinit()

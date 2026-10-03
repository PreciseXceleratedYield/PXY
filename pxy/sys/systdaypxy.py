#!/usr/bin/env python3
import yfinance as yf
from colorama import Fore, Style, init, deinit
from syscnfgpxy import TICKER
import pytz
from datetime import datetime, timedelta, time
from syscnfgpxy import SYSCNFGPXY_TIMEZONE
from sysmodepxy import dispatch_mode

init(autoreset=True)

# ---- ADDED: DARK COLORS ----
dark_green = Style.DIM + Fore.GREEN
dark_red = Style.DIM + Fore.RED

WIDTH = 42

# ---------------- HEADER ----------------
def print_header(today_close, prev_close):
    text = "🏦 PXY® PreciseXceleratedYield Pvt Ltd🏦 "
    if prev_close is None:
        color = Fore.YELLOW
    elif today_close > prev_close:
        color = dark_green
    elif today_close < prev_close:
        color = dark_red
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
        color = dark_green
    else:
        lower = (c - l) / rng
        body  = (o - c) / rng
        color = dark_red
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


# ---------------- MARKET SNAPSHOT ----------------
def _get_last_two_trading_days_production(TICKER, lookback_days=14):
    IST = pytz.timezone("Asia/Kolkata")
    today = datetime.now(IST).date()

    df = yf.Ticker(TICKER).history(
        start=today - timedelta(days=lookback_days),
        end=today + timedelta(days=1)
    )
    if df.empty or len(df) < 2:
        return None, None

    return df.iloc[-1], df.iloc[-2]


def get_last_two_trading_days(TICKER, lookback_days=14):
    return dispatch_mode(
        "get_last_two_trading_days",
        _get_last_two_trading_days_production,
        TICKER,
        lookback_days,
        test_kwargs={"timezone": SYSCNFGPXY_TIMEZONE},
    )


def get_market_snapshot(TICKER):
    today, prev = get_last_two_trading_days(TICKER)
    if today is None or prev is None:
        return None

    # ---------------- INTEGER CONVERSION ONLY ----------------
    o = int(round(today.Open))
    h = int(round(today.High))
    l = int(round(today.Low))
    c = int(round(today.Close))
    prev_close = int(round(prev.Close))

    result = {
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "prev_close": prev_close
    }

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

    # -------- % CALCULATIONS --------
    o_change = ((c - o) / o) * 100 if o != 0 else 0
    m_change = ((c - midpoint) / midpoint) * 100 if midpoint != 0 else 0

    result["o_change"] = round(o_change, 2)
    result["m_change"] = round(m_change, 2)

    # -------- BREAKOUT --------
    IST = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(IST).time()
    breakout = "NA"

    try:
        df_1m = dispatch_mode(
            "get_intraday_data",
            lambda: yf.Ticker(TICKER).history(period="1d", interval="1m"),
            test_kwargs={"ticker": TICKER, "timezone": SYSCNFGPXY_TIMEZONE},
        )
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
    except Exception:
        breakout = "NA"

    result["breakout"] = breakout
    return result


# ---------------- MAIN ----------------
def main():
    data = get_market_snapshot(TICKER)
    if not data:
        print("No data")
        return

    o, h, l, c = data["open"], data["high"], data["low"], data["close"]
    prev_close = data["prev_close"]

    print_header(c, prev_close)
    print_candle(o, h, l, c)

    bias = data["bias"]
    power = data["power"]
    breakout = data["breakout"]
    o_change = data["o_change"]
    m_change = data["m_change"]

    # -------- BIAS + TODAY OPEN --------
    left_label = Fore.YELLOW + "Bias:"
    left_value = (dark_green if "BULL" in bias else dark_red) + bias

    right_label = Fore.YELLOW + "Open:"
    open_color = dark_green if o > prev_close else dark_red if o < prev_close else Fore.YELLOW
    right_value = open_color + f"{o}"

    spacing = WIDTH - len(f"Bias:{bias}") - len(f"Open:{o}")

    print(left_label + left_value + " " * spacing + right_label + right_value)

    # -------- YESTERDAY CLOSE + % --------
    o_str = f"O:{o_change:+.2f}%"
    m_str = f"M:{m_change:+.2f}%"

    left_part = f"YC:{prev_close}"
    mid_part = o_str
    right_part = m_str

    mid_start = (WIDTH // 2) - (len(mid_part) // 2)
    right_start = WIDTH - len(right_part)

    line = [" "] * WIDTH

    for i, ch in enumerate(left_part):
        if i < WIDTH:
            line[i] = ch

    for i, ch in enumerate(mid_part):
        pos = mid_start + i
        if 0 <= pos < WIDTH:
            line[pos] = ch

    for i, ch in enumerate(right_part):
        pos = right_start + i
        if 0 <= pos < WIDTH:
            line[pos] = ch

    final_line = "".join(line)

    o_color = dark_green if o_change > 0 else dark_red if o_change < 0 else Fore.YELLOW
    m_color = dark_green if m_change > 0 else dark_red if m_change < 0 else Fore.YELLOW

    final_line = final_line.replace(o_str, o_color + o_str + Style.RESET_ALL)
    final_line = final_line.replace(m_str, m_color + m_str + Style.RESET_ALL)

    print(final_line)


# ---------------- RUN ----------------
if __name__ == "__main__":
    main()
    deinit()

# sysentrpxy.py
import pandas as pd
import pytz
from datetime import time
from colorama import Fore, Style, init
from sysdtafpxy import fetch_yf_data

# Initialize Colorama
init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")
DEBUG = False

def get_entry_signal(df: pd.DataFrame):
    """
    Returns deterministic entry and exit signals:
    Entry: ATMBUY / ATMSELL / BULL / BEAR / NONE
    Exit: BUY / SELL / BULL / BEAR / NONE

    Special time-based rules:
    - 9:00–9:16 IST: NONE / NONE
    - 9:16–9:20 IST: raw close comparison (UP->ATMBUY/BUY, DOWN->ATMSELL/SELL)
    - Rest of day: V/inverted V detection + trend fallback
    """
    if df is None or len(df) < 2:
        return "NONE", "NONE"

    df = df.copy()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert(IST)
    else:
        df.index = df.index.tz_convert(IST)

    last_time = df.index[-1].time()
    ha_close = df['Close']  # HA close for entry detection
    raw_close = df['Close']  # Raw close for exit detection

    # -------------------- 9:00–9:16 IST: No signals --------------------
    if time(9, 0) <= last_time < time(9, 16):
        return "NONE", "NONE"

    # -------------------- 9:16–9:20 IST: raw close direction --------------------
    if time(9, 16) <= last_time <= time(9, 20):
        if raw_close.iloc[-1] >= raw_close.iloc[-2]:
            return "ATMBUY", "BUY"
        else:
            return "ATMSELL", "SELL"

    # -------------------- Normal V/Inverted V detection --------------------
    entry_signal = "NONE"
    exit_signal = "NONE"

    for i in range(len(df) - 2):
        c1_h, c2_h, c3_h = ha_close.iloc[i], ha_close.iloc[i+1], ha_close.iloc[i+2]
        c1_r, c2_r, c3_r = raw_close.iloc[i], raw_close.iloc[i+1], raw_close.iloc[i+2]

        # Entry detection (HA Close)
        if entry_signal == "NONE":
            if c2_h < c1_h and c2_h < c3_h:
                entry_signal = "ATMBUY"
            elif c2_h > c1_h and c2_h > c3_h:
                entry_signal = "ATMSELL"

        # Exit detection (Raw Close)
        if exit_signal == "NONE":
            if c2_r < c1_r and c2_r < c3_r:
                exit_signal = "BUY"
            elif c2_r > c1_r and c2_r > c3_r:
                exit_signal = "SELL"

        if entry_signal != "NONE" and exit_signal != "NONE":
            break

    # -------------------- Trend fallback --------------------
    if entry_signal == "NONE":
        entry_signal = "BULL" if ha_close.iloc[-1] >= ha_close.iloc[-2] else "BEAR"
    if exit_signal == "NONE":
        exit_signal = "BULL" if raw_close.iloc[-1] >= raw_close.iloc[-2] else "BEAR"

    return entry_signal, exit_signal


# -------------------- Dashboard --------------------
def print_dashboard(df):
    entry_signal, exit_signal = get_entry_signal(df)
    color_map = {
        "ATMBUY": Fore.GREEN, "ATMSELL": Fore.RED,
        "BUY": Fore.GREEN, "SELL": Fore.RED,
        "BULL": Fore.CYAN, "BEAR": Fore.MAGENTA,
        "NONE": Fore.YELLOW
    }
    left_text = f"{color_map.get(entry_signal, Fore.YELLOW)}Entry: {entry_signal}{Style.RESET_ALL}"
    right_text = f"{color_map.get(exit_signal, Fore.YELLOW)}Exit: {exit_signal}{Style.RESET_ALL}"
    print(f"{left_text:<25}{right_text:>25}")


# -------------------- Self-test --------------------
if __name__ == "__main__":
    df = fetch_yf_data()
    if df is not None and not df.empty:
        print_dashboard(df)

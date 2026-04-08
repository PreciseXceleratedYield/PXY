# sysentrpxy.py
import pandas as pd
import pytz
from colorama import Fore, Style, init
from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend

# -------------------- CONFIG --------------------
init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")
DEBUG = False  # Set True to see signal flow

# -------------------- Deterministic Entry Signal with Morning Logic --------------------
def get_entry_signal(df: pd.DataFrame):
    """
    Morning logic:
    - 08:55–09:15 IST → no signal (None)
    - 09:16–09:26 IST → only last 2 candles (C1 vs C2) for raw BUY/SELL, always ATM
    - After 09:26 IST → normal logic using SuperTrend for ATM/OTM
    """
    if df is None or len(df) < 2:
        if DEBUG:
            print("Not enough data for signal.")
        return None, None  # Not enough data

    df = df.copy()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert(IST)
    else:
        df.index = df.index.tz_convert(IST)

    now = df.index[-1].time()
    if DEBUG:
        print(f"Current IST time: {now}")

    # -------------------- Before Morning Session --------------------
    if now < pd.to_datetime("09:15").time():
        if DEBUG:
            print("Before 09:15 → no signal.")
        return None, None  # 08:55–09:15 → no signal

    # -------------------- Morning Session: 09:16–09:26 --------------------
    if pd.to_datetime("09:16").time() <= now <= pd.to_datetime("09:26").time():
        last_two = df['Close'].iloc[-2:]
        if DEBUG:
            print(f"Morning window 09:16–09:26: last_two closes = {last_two.tolist()}")
        if last_two.iloc[-1] > last_two.iloc[-2]:
            return "ATMBUY", "BUY"
        elif last_two.iloc[-1] < last_two.iloc[-2]:
            return "ATMSELL", "SELL"
        else:
            return "ATMBUY", "BUY"  # fallback if equal

    # -------------------- After 09:26 IST → Normal Logic --------------------
    closes = df['Close']
    st_series = df['ST'] if 'ST' in df.columns else closes

    # Determine raw signal (BUY/SELL) by last candle
    if closes.iloc[-1] > closes.iloc[-2]:
        raw_signal = "BUY"
    elif closes.iloc[-1] < closes.iloc[-2]:
        raw_signal = "SELL"
    else:
        raw_signal = "BUY"  # fallback if equal

    last_close = closes.iloc[-1]
    last_st = st_series.iloc[-1]

    # -------------------- Exclusive SELL logic --------------------
    if raw_signal == "BUY":
        entry_signal = "ATMBUY" if last_close >= last_st else "OTMBUY"
    elif raw_signal == "SELL":
        entry_signal = "ATMSELL" if last_close <= last_st else "OTMSELL"
    else:
        entry_signal = None  # No signal

    if DEBUG:
        print(f"Last Close: {last_close}, Last ST: {last_st}")
        print(f"Raw Signal: {raw_signal}, Entry Signal: {entry_signal}")

    return entry_signal, raw_signal

# -------------------- Dashboard --------------------
def print_dashboard(df):
    entry_signal, exit_signal = get_entry_signal(df)
    color_map = {
        "ATMBUY": Fore.GREEN, "OTMBUY": Fore.GREEN,
        "ATMSELL": Fore.RED, "OTMSELL": Fore.RED,
        "BUY": Fore.GREEN, "SELL": Fore.RED
    }

    if entry_signal is None:
        left_text = f"{Fore.YELLOW}Entry: NO SIGNAL{Style.RESET_ALL}"
        right_text = f"{Fore.YELLOW}Exit: NO SIGNAL{Style.RESET_ALL}"
    else:
        left_text = f"{color_map.get(entry_signal, Fore.YELLOW)}Entry: {entry_signal}{Style.RESET_ALL}"
        right_text = f"{color_map.get(exit_signal, Fore.YELLOW)}Exit: {exit_signal}{Style.RESET_ALL}"

    print(f"{left_text:<25}{right_text:>25}")

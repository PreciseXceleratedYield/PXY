# sysentrpxy.py
import pandas as pd
import pytz
from colorama import Fore, Style, init
from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend

# Initialize Colorama
init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")
DEBUG = False

# -------------------- Deterministic Entry Signal --------------------
def get_entry_signal(df: pd.DataFrame):
    """
    Deterministic price-action signal for the whole day:
    - Morning logic:
        - 08:55–09:15 IST → no signal (None)
        - 09:16–09:26 IST → only last 2 candles (C1 vs C2), always ATM
    - C1 = forming candle (last)
    - Fallback chain: C1 vs C2 → C2 vs C3 → C3 vs C4 → ...
    - Entry = ATM/OTM based on SuperTrend
    - Exit = raw BUY/SELL
    - Signal is never None (except morning no-signal window)
    """
    if df is None or len(df) < 2:
        return None, None  # not enough data

    df = df.copy()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert(IST)
    else:
        df.index = df.index.tz_convert(IST)

    now = df.index[-1].time()

    # -------------------- Morning Logic --------------------
    if now < pd.to_datetime("09:15").time():
        # 08:55–09:15 → no signal
        return None, None
    elif pd.to_datetime("09:16").time() <= now <= pd.to_datetime("09:26").time():
        # 09:16–09:26 → compare only last 2 closes, always ATM
        last_two = df['Close'].iloc[-2:]
        if last_two.iloc[-1] > last_two.iloc[-2]:
            return "ATMBUY", "BUY"
        elif last_two.iloc[-1] < last_two.iloc[-2]:
            return "ATMSELL", "SELL"
        else:
            return "ATMBUY", "BUY"  # fallback if equal

    # -------------------- After Morning → Normal Logic --------------------
    closes = df['Close']
    st_series = df['ST'] if 'ST' in df.columns else closes

    # Deterministic raw signal
    raw_signal = None
    for i in range(len(closes)-1, 0, -1):
        if closes.iloc[i] > closes.iloc[i-1]:
            raw_signal = "BUY"
            break
        elif closes.iloc[i] < closes.iloc[i-1]:
            raw_signal = "SELL"
            break
    if raw_signal is None:
        raw_signal = "BUY"  # fallback default

    # -------------------- Exclusive Entry Signal Mapping (ATM/OTM) --------------------
    last_close = closes.iloc[-1]
    last_st = st_series.iloc[-1]

    if raw_signal == "BUY":
        entry_signal = "ATMBUY" if last_close >= last_st else "OTMBUY"
    elif raw_signal == "SELL":
        entry_signal = "ATMSELL" if last_close <= last_st else "OTMSELL"
    else:
        entry_signal = None  # safety fallback

    return entry_signal, raw_signal

# -------------------- Dashboard (optional) --------------------
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

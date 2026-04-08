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
    - C1 = forming candle (last)
    - Fallback chain: C1 vs C2 → C2 vs C3 → C3 vs C4 → ...
    - Entry = ATM/OTM based on SuperTrend
    - Exit = raw BUY/SELL
    - Signal is never None
    """
    if df is None or len(df) < 3:
        return "ATMBUY", "BUY"  # default fallback

    df = df.copy()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert(IST)
    else:
        df.index = df.index.tz_convert(IST)

    closes = df['Close']
    st_series = df['ST'] if 'ST' in df.columns else closes

    # -------------------- Deterministic Raw Signal --------------------
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

    # -------------------- Entry Signal Mapping (ATM/OTM) --------------------
    last_close = closes.iloc[-1]
    last_st = st_series.iloc[-1]

    # Strict exclusive mapping
    if raw_signal == "BUY":
        if last_close > last_st:
            entry_signal = "ATMBUY"
        else:
            entry_signal = None  # no signal if not strictly above
    elif raw_signal == "SELL":
        if last_close < last_st:
            entry_signal = "ATMSELL"
        else:
            entry_signal = None  # no signal if not strictly below
    else:
        entry_signal = None  # safety, though raw_signal should be BUY/SELL
    
    return entry_signal, raw_signal

# -------------------- Dashboard (optional) --------------------
def print_dashboard(df):
    entry_signal, exit_signal = get_entry_signal(df)
    color_map = {
        "ATMBUY": Fore.GREEN, "OTMBUY": Fore.GREEN,
        "ATMSELL": Fore.RED, "OTMSELL": Fore.RED,
        "BUY": Fore.GREEN, "SELL": Fore.RED
    }
    left_text = f"{color_map.get(entry_signal, Fore.YELLOW)}Entry: {entry_signal}{Style.RESET_ALL}"
    right_text = f"{color_map.get(exit_signal, Fore.YELLOW)}Exit: {exit_signal}{Style.RESET_ALL}"
    print(f"{left_text:<25}{right_text:>25}")

# -------------------- Self-test --------------------
if __name__ == "__main__":
    df = fetch_yf_data()
    if df is not None and not df.empty:
        df = calculate_supertrend(df)  # needed for ATM/OTM
    print_dashboard(df)

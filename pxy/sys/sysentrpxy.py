# sysentrpxy.py
import pandas as pd
from datetime import datetime, time
import pytz
from colorama import Fore, Style, init

from sysdtafpxy import fetch_yf_data
from syshkinpxy import detect_ha_flip_signal
from sysstrndpxy import calculate_supertrend
from sysbbospxy import get_bos_bar

# Initialize Colorama
init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")

# -------------------- Morning Direction --------------------
def _get_morning_direction(df: pd.DataFrame):
    if df is None or len(df) < 2:
        return None
    try:
        df = df.copy()
        df.index = pd.to_datetime(df.index)
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert(IST)
        else:
            df.index = df.index.tz_convert(IST)
        df['time'] = df.index.time
        c1_df = df[df['time'] == time(9, 15)]
        if c1_df.empty:
            return None
        c1 = c1_df.iloc[-1]
        c2 = df.iloc[-1]
        if c2['Close'] > c1['Close']:
            return "BUY"
        elif c2['Close'] < c1['Close']:
            return "SELL"
    except Exception:
        return None
    return None

# -------------------- Compute Raw Signal --------------------
def _compute_raw_signal(df: pd.DataFrame) -> str:
    if df is None or not all(col in df.columns for col in ['Open','High','Low','Close']):
        return None

    now = datetime.now(IST).time()
    last = df.iloc[-1]

    if 'ST' not in df.columns:
        df = calculate_supertrend(df)

    # --- Morning Phase ---
    if time(9,14) <= now <= time(9,16):
        return None  # Early morning, no signal
    if time(9,17) <= now <= time(9,30):
        direction = _get_morning_direction(df)
        if direction == "BUY":
            return "MBUY"
        if direction == "SELL":
            return "MSELL"

    # --- BOS Phase ---
    try:
        _, bos_val = get_bos_bar(df)
        if bos_val == "BULL":
            return "BBUY"
        if bos_val == "BEAR":
            return "BSELL"
    except Exception:
        pass

    # --- Reversal Phase ---
    ha_signal, _, _, _ = detect_ha_flip_signal(df)
    if ha_signal in ["RBUY", "RSELL"]:
        return ha_signal

    # --- HA Signals Upgrade ---
    if ha_signal in ["BUY", "BULL"]:
        return "SBUY"
    if ha_signal in ["SELL", "BEAR"]:
        return "SSELL"

    if ha_signal in ["SBUY", "SSELL"]:
        return ha_signal

    return None

# -------------------- Map Raw Signal to Entry (ATM/OTM) --------------------
def get_entry_signal(df: pd.DataFrame):
    raw_signal = _compute_raw_signal(df)
    if df is None or df.empty or raw_signal is None:
        return None, None

    last = df.iloc[-1]
    st_value = df['ST'].iloc[-1] if 'ST' in df.columns else last['Close']

    # --- Morning signals → always ATMBUY / ATMSELL
    if raw_signal in ["MBUY", "MSELL"]:
        entry_signal = "ATMBUY" if raw_signal == "MBUY" else "ATMSELL"
        exit_signal = "BUY" if raw_signal == "MBUY" else "SELL"
        return entry_signal, exit_signal

    # BOS signals → BUY/SELL + ATM/OTM
    if raw_signal in ["BBUY", "BSELL"]:
        exit_signal = "BUY" if raw_signal == "BBUY" else "SELL"
        if exit_signal == "BUY":
            entry_signal = "ATMBUY" if last['Close'] > st_value else "OTMBUY"
        else:
            entry_signal = "ATMSELL" if last['Close'] < st_value else "OTMSELL"
        return entry_signal, exit_signal

    # Reversal signals → BUY/SELL + ATM/OTM
    if raw_signal in ["RBUY", "RSELL"]:
        exit_signal = "BUY" if raw_signal == "RBUY" else "SELL"
        if exit_signal == "BUY":
            entry_signal = "ATMBUY" if last['Close'] > st_value else "OTMBUY"
        else:
            entry_signal = "ATMSELL" if last['Close'] < st_value else "OTMSELL"
        return entry_signal, exit_signal

    # HA signals → SBUY / SSELL / BUY / SELL
    if raw_signal in ["SBUY", "SSELL", "BUY", "SELL"]:
        exit_signal = "BUY" if raw_signal in ["SBUY", "BUY"] else "SELL"
        if exit_signal == "BUY":
            entry_signal = "ATMBUY" if last['Close'] > st_value else "OTMBUY"
        else:
            entry_signal = "ATMSELL" if last['Close'] < st_value else "OTMSELL"
        return entry_signal, exit_signal

    return None, None

# -------------------- Dashboard --------------------
def print_dashboard(df):
    entry_signal, exit_signal = get_entry_signal(df)
    color_map = {
        "ATMBUY": Fore.GREEN, "ATMSELL": Fore.RED,
        "OTMBUY": Fore.GREEN, "OTMSELL": Fore.RED,
        "BUY": Fore.GREEN, "SELL": Fore.RED,
        None: Fore.YELLOW
    }
    left_text = f"{color_map.get(entry_signal, Fore.YELLOW)}Entry: {entry_signal}{Style.RESET_ALL}"
    right_text = f"{color_map.get(exit_signal, Fore.YELLOW)}Exit: {exit_signal}{Style.RESET_ALL}"
    print(f"{left_text:<25}{right_text:>25}")

# -------------------- Self-test --------------------
if __name__ == "__main__":
    df = fetch_yf_data()
    if df is not None and not df.empty:
        df = calculate_supertrend(df)
    print_dashboard(df)

# sysentrpxy.py
import pandas as pd
from datetime import datetime, time
import pytz
from colorama import Fore, Style, init

from sysdtafpxy import fetch_yf_data
from syshkinpxy import detect_ha_flip_signal
from sysstrndpxy import calculate_supertrend
from sysbbospxy import get_bos, get_bos_bar

# Initialize Colorama
init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")

DEBUG = False  # <-- Enable/disable debugging

# -------------------- Morning Direction --------------------
def _get_morning_direction(df: pd.DataFrame):
    if df is None or len(df) < 2:
        if DEBUG: print("[DEBUG] _get_morning_direction: Not enough data")
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
            if DEBUG: print("[DEBUG] _get_morning_direction: 9:15 candle not found")
            return None
        c1 = c1_df.iloc[-1]
        c2 = df.iloc[-1]
        if DEBUG: print(f"[DEBUG] Morning Candles: c1={c1['Close']}, c2={c2['Close']}")
        if c2['Close'] > c1['Close']:
            return "BUY"
        elif c2['Close'] < c1['Close']:
            return "SELL"
    except Exception as e:
        if DEBUG: print(f"[DEBUG] _get_morning_direction exception: {e}")
        return None
    return None

# -------------------- Compute Raw Signal (Priority: Morning → BOS → HA) --------------------
def _compute_raw_signal(df: pd.DataFrame) -> str:
    if df is None or not all(col in df.columns for col in ['Open','High','Low','Close']):
        if DEBUG: print("[DEBUG] _compute_raw_signal: DataFrame missing required columns")
        return "NONE"

    now = datetime.now(IST).time()
    
    # --- Morning Phase ---
    if time(9,14) <= now <= time(9,16):
        if DEBUG: print("[DEBUG] Early morning phase, no signal")
        return "NONE"
    if time(9,17) <= now <= time(9,30):
        direction = _get_morning_direction(df)
        if DEBUG: print(f"[DEBUG] Morning direction: {direction}")
        if direction == "BUY":
            return "MBUY"
        if direction == "SELL":
            return "MSELL"

    # --- BOS Phase (priority) ---
    try:
        bos_signal = get_bos(df)  # BBUY/BSELL/RBUY/RSELL/NONE
        if DEBUG: print(f"[DEBUG] BOS signal: {bos_signal}")
        if bos_signal != "NONE":
            return bos_signal
    except Exception as e:
        if DEBUG: print(f"[DEBUG] get_bos exception: {e}")

    # --- HA Phase fallback ---
    ha_signal, _, _, _ = detect_ha_flip_signal(df)
    if DEBUG: print(f"[DEBUG] HA flip signal: {ha_signal}")

    if ha_signal in ["RBUY", "RSELL"]:
        return ha_signal
    if ha_signal in ["BUY", "BULL"]:
        return "SBUY"
    if ha_signal in ["SELL", "BEAR"]:
        return "SSELL"
    if ha_signal in ["SBUY", "SSELL"]:
        return ha_signal
    if ha_signal in ["BULL", "BEAR"]:
        return ha_signal  # keep as-is

    return "NONE"

# -------------------- Map Raw Signal to Entry/Exit --------------------
def get_entry_signal(df: pd.DataFrame):
    raw_signal = _compute_raw_signal(df)
    if DEBUG: print(f"[DEBUG] Raw signal: {raw_signal}")

    if df is None or df.empty or raw_signal in [None, "NONE"]:
        return None, None

    last = df.iloc[-1]
    st_value = df['ST'].iloc[-1] if 'ST' in df.columns else last['Close']

    # --- Entry signal conversion ---
    if raw_signal == "MBUY":
        entry_signal = "ATMBUY"  # Morning → always ATM
    elif raw_signal == "MSELL":
        entry_signal = "ATMSELL"  # Morning → always ATM
    elif raw_signal in ["BBUY", "RBUY", "SBUY"]:
        entry_signal = "ATMBUY" if last['Close'] > st_value else "OTMBUY"
    elif raw_signal in ["BSELL", "RSELL", "SSELL"]:
        entry_signal = "ATMSELL" if last['Close'] < st_value else "OTMSELL"
    else:
        entry_signal = None  # e.g., HA BULL / BEAR

    # --- Exit signal remains raw signal ---
    exit_signal = raw_signal

    if DEBUG: print(f"[DEBUG] Mapped entry: {entry_signal}, exit: {exit_signal}")
    return entry_signal, exit_signal

# -------------------- Dashboard --------------------
def print_dashboard(df):
    entry_signal, exit_signal = get_entry_signal(df)
    color_map = {
        "ATMBUY": Fore.GREEN, "ATMSELL": Fore.RED,
        "OTMBUY": Fore.GREEN, "OTMSELL": Fore.RED,
        "BUY": Fore.GREEN, "SELL": Fore.RED,
        "BULL": Fore.CYAN, "BEAR": Fore.MAGENTA,
        None: Fore.YELLOW
    }
    left_text = f"{color_map.get(entry_signal, Fore.YELLOW)}Entry: {entry_signal}{Style.RESET_ALL}"
    right_text = f"{color_map.get(exit_signal, Fore.YELLOW)}Exit: {exit_signal}{Style.RESET_ALL}"
    print(f"{left_text:<25}{right_text:>25}")

# -------------------- Self-test --------------------
if __name__ == "__main__":
    if DEBUG: print("[DEBUG] Fetching YF data...")
    df = fetch_yf_data()
    if df is not None and not df.empty:
        if DEBUG: print("[DEBUG] Calculating SuperTrend for self-test...")
        df = calculate_supertrend(df)
    print_dashboard(df)

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

DEBUG = True  # <-- Enable/disable debugging

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

# -------------------- Compute Raw Signal --------------------
def _compute_raw_signal(df: pd.DataFrame) -> str:
    if df is None or not all(col in df.columns for col in ['Open','High','Low','Close']):
        if DEBUG: print("[DEBUG] _compute_raw_signal: DataFrame missing required columns")
        return None

    now = datetime.now(IST).time()
    last = df.iloc[-1]

    if 'ST' not in df.columns:
        if DEBUG: print("[DEBUG] Calculating SuperTrend...")
        df = calculate_supertrend(df)
        if DEBUG: print("[DEBUG] SuperTrend calculated")

    # --- Morning Phase ---
    if time(9,14) <= now <= time(9,16):
        if DEBUG: print("[DEBUG] Early morning phase, no signal")
        return None
    if time(9,17) <= now <= time(9,30):
        direction = _get_morning_direction(df)
        if DEBUG: print(f"[DEBUG] Morning direction: {direction}")
        if direction == "BUY":
            return "MBUY"
        if direction == "SELL":
            return "MSELL"

    # --- BOS Phase ---
    try:
        _, bos_val = get_bos_bar(df)
        if DEBUG: print(f"[DEBUG] BOS value: {bos_val}")
        if bos_val == "BULL":
            return "BBUY"
        if bos_val == "BEAR":
            return "BSELL"
    except Exception as e:
        if DEBUG: print(f"[DEBUG] get_bos_bar exception: {e}")

    # --- Reversal Phase ---
    ha_signal, _, _, _ = detect_ha_flip_signal(df)
    if DEBUG: print(f"[DEBUG] HA flip signal: {ha_signal}")
    if ha_signal in ["RBUY", "RSELL"]:
        return ha_signal

    # --- HA Signals Upgrade ---
    if ha_signal in ["BUY", "BULL"]:
        return "SBUY"
    if ha_signal in ["SELL", "BEAR"]:
        return "SSELL"

    if ha_signal in ["SBUY", "SSELL"]:
        return ha_signal

    if DEBUG: print("[DEBUG] No raw signal detected")
    return None

# -------------------- Map Raw Signal to Entry (ATM/OTM) --------------------
def get_entry_signal(df: pd.DataFrame):
    raw_signal = _compute_raw_signal(df)
    if DEBUG: print(f"[DEBUG] Raw signal: {raw_signal}")

    if df is None or df.empty or raw_signal is None:
        return None, None

    last = df.iloc[-1]
    st_value = df['ST'].iloc[-1] if 'ST' in df.columns else last['Close']

    # --- Morning signals → always ATMBUY / ATMSELL
    if raw_signal in ["MBUY", "MSELL"]:
        entry_signal = "ATMBUY" if raw_signal == "MBUY" else "ATMSELL"
        exit_signal = "BUY" if raw_signal == "MBUY" else "SELL"
        if DEBUG: print(f"[DEBUG] Morning signal mapped: {entry_signal}, {exit_signal}")
        return entry_signal, exit_signal

    # BOS, Reversal, HA signals
    mapping = {
        "BBUY": "BUY", "BSELL": "SELL",
        "RBUY": "BUY", "RSELL": "SELL",
        "SBUY": "BUY", "SSELL": "SELL",
        "BUY": "BUY", "SELL": "SELL"
    }

    if raw_signal in mapping:
        exit_signal = mapping[raw_signal]
        # Strict direction-based ATM/OTM mapping
        if exit_signal == "BUY":
            entry_signal = "ATMBUY" if last['Close'] > st_value else "OTMBUY"
        else:  # SELL
            entry_signal = "ATMSELL" if last['Close'] < st_value else "OTMSELL"
        if DEBUG: print(f"[DEBUG] Mapped entry/exit: {entry_signal}, {exit_signal}")
        return entry_signal, exit_signal

    if DEBUG: print("[DEBUG] No entry/exit mapping found")
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
    if DEBUG: print("[DEBUG] Fetching YF data...")
    df = fetch_yf_data()
    if df is not None and not df.empty:
        if DEBUG: print("[DEBUG] Calculating SuperTrend for self-test...")
        df = calculate_supertrend(df)
    print_dashboard(df)

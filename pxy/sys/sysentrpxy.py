# sysentrpxy.py
import pandas as pd
from datetime import datetime, time
import pytz
from colorama import Fore, Style, init

from sysdtafpxy import fetch_yf_data
from sysmktpxy import detect_ha_flip_signal
from sysstrndpxy import calculate_supertrend

init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")

# -------------------- STATE MEMORY --------------------
_last_valid_signal = None


# -------------------- Morning direction --------------------
def _get_morning_direction(df: pd.DataFrame):
    """Returns exclusive morning signal: OTMBUY or OTMSELL"""
    if df is None or len(df) < 2:
        return None

    try:
        last = df.iloc[-1]
        prev = df.iloc[-2]

        if last['Close'] > prev['Close']:
            return "OTMBUY"
        elif last['Close'] < prev['Close']:
            return "OTMSELL"
        else:
            return None

    except Exception as e:
        print(f"[ERROR] Morning Direction: {e}")
        return None


# -------------------- Core ENTRY signal --------------------
def _compute_final_signal(df: pd.DataFrame) -> str:
    """Primary entry signal (UNCHANGED LOGIC)"""

    if df is None or not all(col in df.columns for col in ['Open','High','Low','Close']):
        return "DEFAULT"

    now = datetime.now(IST).time()
    last = df.iloc[-1]

    # Ensure Supertrend
    if 'ST' not in df.columns:
        df = calculate_supertrend(df)

    st_value = df['ST'].iloc[-1]

    # 🔵 PHASE 0
    if time(9, 0) <= now <= time(9, 16):
        return "DEFAULT"

    # 🟡 PHASE 1
    if time(9, 16) < now <= time(9, 25):
        direction_signal = _get_morning_direction(df)
        return direction_signal if direction_signal else "DEFAULT"

    # 🟢 PHASE 2
    try:
        ha_signal, _, _, _ = detect_ha_flip_signal(df)

        if ha_signal == "BULL":
            return "BULL"

        elif ha_signal == "BEAR":
            return "BEAR"

        elif ha_signal == "BUY":
            return "ATMBUY" if last['Close'] >= st_value else "OTMBUY"

        elif ha_signal == "SELL":
            return "ATMSELL" if last['Close'] <= st_value else "OTMSELL"

        else:
            return "DEFAULT"

    except Exception as e:
        print(f"[ERROR] HA Logic: {e}")
        return "DEFAULT"


# -------------------- EXIT VALIDATION --------------------
def _validate_with_raw_direction(df: pd.DataFrame, entry_signal: str) -> str:
    """
    Validate signal using last 2 CLOSE direction
    """
    if df is None or len(df) < 2 or entry_signal is None:
        return None

    try:
        last = df.iloc[-1]
        prev = df.iloc[-2]

        if last['Close'] > prev['Close']:
            direction = "UP"
        elif last['Close'] < prev['Close']:
            direction = "DOWN"
        else:
            return None

        if direction == "UP":
            return entry_signal if entry_signal in ["BULL", "BUY", "ATMBUY", "OTMBUY"] else None

        elif direction == "DOWN":
            return entry_signal if entry_signal in ["BEAR", "SELL", "ATMSELL", "OTMSELL"] else None

        return None

    except Exception as e:
        print(f"[ERROR] Exit Validation: {e}")
        return None


# -------------------- Public function (STATE ENGINE + SAFE OUTPUT) --------------------
def get_entry_signal(df: pd.DataFrame):
    """
    - Pure state engine internally
    - Always returns SAFE STRINGS externally
    """
    global _last_valid_signal

    raw_entry = _compute_final_signal(df)

    # -------- STATE LOGIC --------
    if raw_entry not in [None, "DEFAULT"]:
        _last_valid_signal = raw_entry

    entry = _last_valid_signal  # hold last signal

    # -------- EXIT --------
    exit_signal = _validate_with_raw_direction(df, entry) if entry else None

    # -------- SAFE OUTPUT (CRITICAL) --------
    entry = entry if entry is not None else "DEFAULT"
    exit_signal = exit_signal if exit_signal is not None else "DEFAULT"

    return entry, exit_signal


# -------------------- Terminal dashboard --------------------
def print_dashboard(df):
    entry, exit_signal = get_entry_signal(df)

    color_map = {
        "OTMBUY": Fore.GREEN, "OTMSELL": Fore.RED,
        "ATMBUY": Fore.GREEN, "ATMSELL": Fore.RED,
        "BULL": Fore.GREEN, "BEAR": Fore.RED,
        "DEFAULT": Fore.YELLOW
    }

    print("\n" + "=" * 60)
    print(f"{'PXY ENTRY / EXIT ENGINE':^60}")
    print("=" * 60)

    print(f"{color_map.get(entry, Fore.YELLOW)}ENTRY : {entry}{Style.RESET_ALL}")
    print(f"{color_map.get(exit_signal, Fore.YELLOW)}EXIT  : {exit_signal}{Style.RESET_ALL}")

    print("=" * 60)


# -------------------- Self-test --------------------
if __name__ == "__main__":
    df = fetch_yf_data()

    if df is not None and not df.empty:
        df = calculate_supertrend(df)

    print_dashboard(df)

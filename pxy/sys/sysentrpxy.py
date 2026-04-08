# sysentrpxy.py
import pandas as pd
from datetime import datetime, time
import pytz
from colorama import Fore, Style, init

from sysdtafpxy import fetch_yf_data
from syshkinpxy import detect_ha_flip_signal
from sysstrndpxy import calculate_supertrend

init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")


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
    - UP → allow only BULL / BUY / ATMBUY / OTMBUY
    - DOWN → allow only BEAR / SELL / ATMSELL / OTMSELL
    - else → DEFAULT
    """
    if df is None or len(df) < 2:
        return "DEFAULT"

    try:
        last = df.iloc[-1]
        prev = df.iloc[-2]

        if last['Close'] > prev['Close']:
            direction = "UP"
        elif last['Close'] < prev['Close']:
            direction = "DOWN"
        else:
            return "DEFAULT"

        # -------- VALIDATION --------
        if direction == "UP":
            if entry_signal in ["BULL", "BUY", "ATMBUY", "OTMBUY"]:
                return entry_signal
            else:
                return "DEFAULT"

        elif direction == "DOWN":
            if entry_signal in ["BEAR", "SELL", "ATMSELL", "OTMSELL"]:
                return entry_signal
            else:
                return "DEFAULT"

        return "DEFAULT"

    except Exception as e:
        print(f"[ERROR] Exit Validation: {e}")
        return "DEFAULT"


# -------------------- Public function --------------------
def get_entry_signal(df: pd.DataFrame):
    """
    Returns:
    entry → raw system signal
    exit  → validated signal (filtered)
    """
    entry = _compute_final_signal(df)
    exit_signal = _validate_with_raw_direction(df, entry)

    return entry, exit_signal


# -------------------- Terminal dashboard --------------------
def print_dashboard(df):
    entry, exit_signal = get_entry_signal(df)

    color_map = {
        "OTMBUY": Fore.GREEN, "OTMSELL": Fore.RED,
        "ATMBUY": Fore.GREEN, "ATMSELL": Fore.RED,
        "BULL": Fore.GREEN, "BEAR": Fore.RED,
        "DEFAULT": Fore.YELLOW, None: Fore.YELLOW
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

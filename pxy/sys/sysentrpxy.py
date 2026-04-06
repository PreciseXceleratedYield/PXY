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
            return "OTMBUY"
        elif c2['Close'] < c1['Close']:
            return "OTMSELL"
        else:
            return None  # exactly equal, no side chosen
    except Exception:
        return None

# -------------------- Core signal computation --------------------
def _compute_final_signal(df: pd.DataFrame) -> str:
    """Compute final signal with mutually exclusive conditions"""
    if df is None or not all(col in df.columns for col in ['Open','High','Low','Close']):
        return "DEFAULT"

    now = datetime.now(IST).time()
    last = df.iloc[-1]

    # Ensure Supertrend column exists
    if 'ST' not in df.columns:
        df = calculate_supertrend(df)
    st_value = df['ST'].iloc[-1] if 'ST' in df.columns else last['Close']

    # -------------------- Phase 0: Early --------------------
    if time(9,14) <= now <= time(9,15):
        return "DEFAULT"

    # -------------------- Phase 1: Morning --------------------
    direction_signal = _get_morning_direction(df)
    if direction_signal:
        return direction_signal

    # -------------------- Phase 2: HA + ST alignment --------------------
    try:
        ha_signal, _, _, _ = detect_ha_flip_signal(df)

        # Exclusive conditions: pick only one signal
        if ha_signal == "BULL":
            return "BULL"
        elif ha_signal == "BEAR":
            return "BEAR"
        elif ha_signal == "BUY":
            if last['Close'] >= st_value:
                return "ATMBUY"
            else:
                return "OTMBUY"
        elif ha_signal == "SELL":
            if last['Close'] <= st_value:
                return "ATMSELL"
            else:
                return "OTMSELL"
    except Exception:
        pass

    # -------------------- Default fallback --------------------
    return "DEFAULT"

# -------------------- Public function --------------------
def get_entry_signal(df: pd.DataFrame):
    """
    Returns two identical values for backward compatibility
    Each signal is exclusive
    """
    final_signal = _compute_final_signal(df)
    return final_signal, final_signal

# -------------------- Terminal dashboard print --------------------
def print_dashboard(df):
    value1, value2 = get_entry_signal(df)
    color_map = {
        "OTMBUY": Fore.GREEN, "OTMSELL": Fore.RED,
        "ATMBUY": Fore.GREEN, "ATMSELL": Fore.RED,
        "BULL": Fore.GREEN, "BEAR": Fore.RED,
        "DEFAULT": Fore.YELLOW, None: Fore.YELLOW
    }
    print(f"{color_map.get(value1, Fore.YELLOW)}Signal: {value1}{Style.RESET_ALL}")

# -------------------- Self-test --------------------
if __name__ == "__main__":
    df = fetch_yf_data()
    if df is not None and not df.empty:
        df = calculate_supertrend(df)
    print_dashboard(df)

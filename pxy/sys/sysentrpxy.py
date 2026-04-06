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
    except Exception:
        return None
    return None

# -------------------- Core signal computation --------------------
def _compute_final_signal(df: pd.DataFrame) -> str:
    if df is None or not all(col in df.columns for col in ['Open','High','Low','Close']):
        return "DEFAULT"

    now = datetime.now(IST).time()
    last = df.iloc[-1]

    # Ensure Supertrend column exists
    if 'ST' not in df.columns:
        df = calculate_supertrend(df)
    st_value = df['ST'].iloc[-1] if 'ST' in df.columns else last['Close']

    # Phase 0: Early
    if time(9,14) <= now <= time(9,15):
        return "DEFAULT"

    # Phase 1: Morning
    direction_signal = _get_morning_direction(df)
    if direction_signal:
        return direction_signal

    # Phase 2: ST + HA alignment
    try:
        last = df.iloc[-1]
        st_value = last['ST']

        ha_signal, _, _, _ = detect_ha_flip_signal(df)

        if ha_signal in ["BULL", "BEAR"]:
            return ha_signal
        elif ha_signal == "BUY":
            return "ATMBUY" if last['Close'] > st_value else "OTMSELL"
        elif ha_signal == "SELL":
            return "ATMSELL" if last['Close'] < st_value else "OTMBUY"

    except Exception:
        pass

    return "DEFAULT"

# -------------------- Public function --------------------
def get_entry_signal(df: pd.DataFrame):
    """
    Returns two values (value1, value2) for backward compatibility
    - Keeps same signals as before
    """
    final_signal = _compute_final_signal(df)
    value1 = final_signal
    value2 = final_signal  # same as value1, can be customized
    return value1, value2

# -------------------- Terminal dashboard print --------------------
def print_dashboard(df):
    value1, value2 = get_entry_signal(df)
    color_map = {
        "OTMBUY": Fore.GREEN, "OTMSELL": Fore.RED,
        "ATMBUY": Fore.GREEN, "ATMSELL": Fore.RED,
        "BULL": Fore.GREEN, "BEAR": Fore.RED,
        "DEFAULT": Fore.YELLOW, None: Fore.YELLOW
    }
    print(f"{color_map.get(value1, Fore.YELLOW)}Signal 1: {value1} | Signal 2: {value2}{Style.RESET_ALL}")

# -------------------- Self-test --------------------
if __name__ == "__main__":
    df = fetch_yf_data()
    if df is not None and not df.empty:
        df = calculate_supertrend(df)
    print_dashboard(df)

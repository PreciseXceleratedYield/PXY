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

# -------------------- Reversal logic --------------------
def _check_reversal(df: pd.DataFrame) -> str:
    if len(df) < 2:
        return "NONE"
    last = df.iloc[-1]
    prev = df.iloc[-2]
    if last['Close'] > last['Open'] and prev['Close'] < prev['Open'] and last['Close'] > prev['High']:
        return "ACTIVE"
    if last['Close'] < last['Open'] and prev['Close'] > prev['Open'] and last['Close'] < prev['Low']:
        return "ACTIVE"
    return "NONE"

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
            return "BUY"
        elif c2['Close'] < c1['Close']:
            return "SELL"
    except Exception:
        return None
    return None

# -------------------- Core signal computation --------------------
def _compute_final_signal(df: pd.DataFrame) -> str:
    if df is None or not all(col in df.columns for col in ['Open','High','Low','Close']):
        return "DEFAULT"

    now = datetime.now(IST).time()
    last = df.iloc[-1]

    if 'ST' not in df.columns:
        df = calculate_supertrend(df)
    st_value = df['ST'].iloc[-1] if 'ST' in df.columns else last['Close']

    # Phase 0: Early
    if time(9,14) <= now <= time(9,15):
        return "DEFAULT"

    # Phase 1: Morning
    if time(9,16) <= now <= time(9,36):
        direction = _get_morning_direction(df)
        if direction == "BUY": return "MBUY"
        if direction == "SELL": return "MSELL"

    # Phase 2: Reversal
    if len(df) >= 2 and _check_reversal(df) == "ACTIVE":
        return "RBUY" if last['Close'] > last['Open'] else "RSELL"

    # Phase 3: BOS
    try:
        _, bos_val = get_bos_bar(df)
        if bos_val == "BULL": return "BBUY"
        if bos_val == "BEAR": return "BSELL"
    except Exception:
        pass

    # Phase 4: ST + HA alignment
    try:
        df = calculate_supertrend(df)
        last = df.iloc[-1]
        st_value = last['ST']

        ha_signal, _, _, _ = detect_ha_flip_signal(df)

        if ha_signal in ["BULL", "BEAR"]:
            return ha_signal
        elif ha_signal == "BUY":
            return "SBUY" if last['Close'] > st_value else "SELL"
        elif ha_signal == "SELL":
            return "SSELL" if last['Close'] < st_value else "BUY"

    except Exception:
        pass

    return None

# -------------------- Public function --------------------
def get_entry_signal(df: pd.DataFrame):
    """
    Returns two signals:
    1️⃣ entry_signal → ATM style based on ST (ATMBUY/ATMSELL) if price confirms
    2️⃣ final_signal → raw signal from phase logic (MBUY, RBUY, BBUY, SBUY, etc.)
    """
    final_signal = _compute_final_signal(df)
    if df is None or df.empty:
        return None, final_signal

    last = df.iloc[-1]
    st_value = df['ST'].iloc[-1] if 'ST' in df.columns else last['Close']

    entry_signal = final_signal
    if final_signal and "BUY" in str(final_signal) and last['Close'] > st_value:
        entry_signal = "ATMBUY"
    elif final_signal and "SELL" in str(final_signal) and last['Close'] < st_value:
        entry_signal = "ATMSELL"

    return entry_signal, final_signal

# -------------------- Optional: dashboard print --------------------
def print_dashboard(df):
    entry_signal, final_signal = get_entry_signal(df)
    color_map = {
        "MBUY": Fore.GREEN, "MSELL": Fore.RED,
        "RBUY": Fore.GREEN, "RSELL": Fore.RED,
        "BBUY": Fore.GREEN, "BSELL": Fore.RED,
        "SBUY": Fore.GREEN, "SSELL": Fore.RED,
        "BUY": Fore.GREEN, "SELL": Fore.RED,
        "BULL": Fore.GREEN, "BEAR": Fore.RED,
        "ATMBUY": Fore.GREEN, "ATMSELL": Fore.RED,
        "DEFAULT": Fore.YELLOW, None: Fore.YELLOW
    }
    left_text = f"{color_map.get(final_signal, Fore.YELLOW)}Final: {final_signal}{Style.RESET_ALL}"
    right_text = f"{color_map.get(entry_signal, Fore.YELLOW)}Entry: {entry_signal}{Style.RESET_ALL}"
    print(f"{left_text:<25}{right_text:>25}")

# -------------------- Self-test --------------------
if __name__ == "__main__":
    df = fetch_yf_data()
    if df is not None and not df.empty:
        df = calculate_supertrend(df)
    print_dashboard(df)

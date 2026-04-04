# sysentrpxy.py

import pandas as pd
from datetime import datetime, time
import pytz

from colorama import Fore, Style, init
from sysdtafpxy import fetch_yf_data
from syshkinpxy import detect_ha_flip_signal
from sysstrndpxy import calculate_supertrend
from sysbbospxy import get_bos_bar

init(autoreset=True)

IST = pytz.timezone("Asia/Kolkata")

# ==========================================================
# --- Reversal logic (UNCHANGED STRUCTURE) ---
# ==========================================================
def check_reversal(df: pd.DataFrame) -> str:

    if len(df) < 2:
        return "None"
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    if (last['Close'] > last['Open'] and
        prev['Close'] < prev['Open'] and
        last['Close'] > prev['High']):
        return "ACTIVE"

    if (last['Close'] < last['Open'] and
        prev['Close'] > prev['Open'] and
        last['Close'] < prev['Low']):
        return "ACTIVE"
    
    return "None"


# ==========================================================
# --- Morning C1 vs C2 ---
# ==========================================================
def get_morning_direction(df: pd.DataFrame):

    if df is None or len(df) < 3:
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


# ==========================================================
# --- Entry signal calculation ---
# ==========================================================
def get_entry_signal(df: pd.DataFrame) -> (str, str):

    required_cols = ['Open', 'High', 'Low', 'Close']
    if df is None or len(df) < 3 or not all(col in df.columns for col in required_cols):
        return "NONE", "None"

    now = datetime.now(IST).time()

    # ======================================================
    # 0️⃣ 9:14–9:15 → NONE
    # ======================================================
    if time(9,14) <= now <= time(9,15):
        return "NONE", "None"

    # ======================================================
    # 1️⃣ MORNING (9:16–9:36)
    # ======================================================
    if time(9,16) <= now <= time(9,36):

        direction = get_morning_direction(df)

        if direction == "BUY":
            return "MBUY", "None"
        elif direction == "SELL":
            return "MSELL", "None"
        else:
            return "WAIT", "None"

    # ======================================================
    # 2️⃣ REVERSAL (USES ORIGINAL STRUCTURE)
    # ======================================================
    reversal_status = check_reversal(df)

    if reversal_status == "ACTIVE":
        last = df.iloc[-1]
        entry_signal = "RBUY" if last['Close'] > last['Open'] else "RSELL"
        return entry_signal, reversal_status

    # ======================================================
    # 3️⃣ BOS
    # ======================================================
    try:
        _, bos_val = get_bos_bar(df)
        if bos_val == "BULL":
            return "BBUY", "None"
        elif bos_val == "BEAR":
            return "BSELL", "None"
    except Exception:
        pass

    # ======================================================
    # 4️⃣ ST + HA ALIGNMENT
    # ======================================================
    try:
        df = calculate_supertrend(df)

        if 'ST' not in df.columns:
            return "NONE", "None"

        st_trend = "UP" if df['Close'].iloc[-1] > df['ST'].iloc[-1] else "DOWN"
        ha_signal, _, _, _ = detect_ha_flip_signal(df)

        if st_trend == "UP" and ha_signal in ["BUY", "BULL"]:
            return "SBUY", "None"
        elif st_trend == "DOWN" and ha_signal in ["SELL", "BEAR"]:
            return "SSELL", "None"

    except Exception:
        pass

    return "NONE", "None"


# ==========================================================
# --- Self-runnable test (UNCHANGED STYLE) ---
# ==========================================================
if __name__ == "__main__":

    df = fetch_yf_data()
    entry_signal, reversal_status = get_entry_signal(df)

    left_text = f"Entry:{entry_signal}"
    right_text = f"Rvrsl:{reversal_status}"
    dashboard_line = f"{left_text:<21}{right_text:>21}"

    if entry_signal in ["BUY","BULL","SBUY","BBUY","RBUY","MBUY"]:
        color = Fore.GREEN
    elif entry_signal in ["SELL","BEAR","SSELL","BSELL","RSELL","MSELL"]:
        color = Fore.RED
    else:
        color = Fore.YELLOW

    print(f"{color}{dashboard_line}{Style.RESET_ALL}")

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
# --- Reversal logic ---
# ==========================================================
def check_reversal(df: pd.DataFrame) -> str:
    if len(df) < 2:
        return "NONE"
    last = df.iloc[-1]
    prev = df.iloc[-2]
    if (last['Close'] > last['Open'] and prev['Close'] < prev['Open'] and last['Close'] > prev['High']):
        return "ACTIVE"
    if (last['Close'] < last['Open'] and prev['Close'] > prev['Open'] and last['Close'] < prev['Low']):
        return "ACTIVE"
    return "NONE"

# ==========================================================
# --- Morning C1 vs C2 ---
# ==========================================================
def get_morning_direction(df: pd.DataFrame):
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

# ==========================================================
# --- Entry signal calculation ---
# ==========================================================
def get_entry_signal(df: pd.DataFrame) -> (str, str):
    required_cols = ['Open', 'High', 'Low', 'Close']
    if df is None or not all(col in df.columns for col in required_cols):
        return "ATMBUY", "DEFAULT"

    now = datetime.now(IST).time()

    # 0️⃣ Early 9:14–9:15 → NONE
    if time(9,14) <= now <= time(9,15):
        return "ATMBUY", "DEFAULT"

    # 1️⃣ Morning 9:16–9:36
    if time(9,16) <= now <= time(9,36):
        direction = get_morning_direction(df)
        if direction == "BUY":
            return "ATMBUY", "MBUY"
        elif direction == "SELL":
            return "ATMSELL", "MSELL"

    # 2️⃣ Reversal
    if len(df) >= 2:
        reversal_status = check_reversal(df)
        if reversal_status == "ACTIVE":
            last = df.iloc[-1]
            entry_signal = "RBUY" if last['Close'] > last['Open'] else "RSELL"
            close_price = last['Close']
            st_value = df['ST'].iloc[-1] if 'ST' in df.columns else close_price
            if entry_signal == "RBUY":
                atm_signal = "ATMBUY" if close_price > st_value else "OTMBUY"
            else:
                atm_signal = "ATMSELL" if close_price < st_value else "OTMSELL"
            return atm_signal, entry_signal

    # 3️⃣ BOS
    try:
        _, bos_val = get_bos_bar(df)
        last = df.iloc[-1]
        st_value = df['ST'].iloc[-1] if 'ST' in df.columns else last['Close']
        if bos_val == "BULL":
            return ("ATMBUY" if last['Close'] > st_value else "OTMBUY", "BBUY")
        elif bos_val == "BEAR":
            return ("ATMSELL" if last['Close'] < st_value else "OTMSELL", "BSELL")
    except Exception:
        pass

    # 4️⃣ ST + HA alignment
    try:
        df = calculate_supertrend(df)
        if 'ST' in df.columns:
            last = df.iloc[-1]
            st_trend = "UP" if last['Close'] > last['ST'] else "DOWN"
            ha_signal, _, _, _ = detect_ha_flip_signal(df)
            st_value = last['ST']
            if st_trend == "UP" and ha_signal in ["BUY", "BULL"]:
                return ("ATMBUY" if last['Close'] > st_value else "OTMBUY", "SBUY")
            elif st_trend == "DOWN" and ha_signal in ["SELL", "BEAR"]:
                return ("ATMSELL" if last['Close'] < st_value else "OTMSELL", "SSELL")
    except Exception:
        pass

    # 5️⃣ Default fallback → always ATM
    last = df.iloc[-1]
    st_value = df['ST'].iloc[-1] if 'ST' in df.columns else last['Close']
    if last['Close'] >= st_value:
        return "ATMBUY", "DEFAULT"
    else:
        return "ATMSELL", "DEFAULT"

# ==========================================================
# --- Self-runnable test ---
# ==========================================================
if __name__ == "__main__":
    df = fetch_yf_data()
    if df is not None and not df.empty:
        df = calculate_supertrend(df)
        final_signal, original_signal = get_entry_signal(df)
    else:
        final_signal, original_signal = "ATMBUY", "DEFAULT"

    # --- Print dashboard line ---
    left_text = f"Entry:{final_signal}"
    right_text = f"Orig:{original_signal}"
    dashboard_line = f"{left_text:<21}{right_text:>21}"

    # --- Color coding ---
    if final_signal in ["ATMBUY","OTMBUY","SBUY","BBUY","RBUY"]:
        color = Fore.GREEN
    elif final_signal in ["ATMSELL","OTMSELL","SSELL","BSELL","RSELL"]:
        color = Fore.RED
    else:
        color = Fore.YELLOW

    print(f"{color}{dashboard_line}{Style.RESET_ALL}")

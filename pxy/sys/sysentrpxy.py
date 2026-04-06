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
        # FORMING vs PREVIOUS CLOSED
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


# -------------------- Core signal computation --------------------
def _compute_final_signal(df: pd.DataFrame) -> str:
    """Compute final signal with mutually exclusive conditions"""

    # ---------- Safety ----------
    if df is None or not all(col in df.columns for col in ['Open','High','Low','Close']):
        return "DEFAULT"

    now = datetime.now(IST).time()
    last = df.iloc[-1]  # forming candle

    # ---------- Ensure Supertrend ----------
    if 'ST' not in df.columns:
        df = calculate_supertrend(df)

    st_value = df['ST'].iloc[-1]

    # =========================================================
    # 🔵 PHASE 0 → 09:00 to 09:16 → STRICT DEFAULT
    # =========================================================
    if time(9, 0) <= now <= time(9, 16):
        return "DEFAULT"

    # =========================================================
    # 🟡 PHASE 1 → 09:16 to 09:25 → PREVIOUS CLOSE COMPARISON
    # =========================================================
    if time(9, 16) < now <= time(9, 25):
        direction_signal = _get_morning_direction(df)
        return direction_signal if direction_signal else "DEFAULT"

    # =========================================================
    # 🟢 PHASE 2 → After 09:25 → HA + ST LOGIC
    # =========================================================
    try:
        ha_signal, _, _, _ = detect_ha_flip_signal(df)

        # -------- STRICT EXCLUSIVE TREE --------
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


# -------------------- Public function --------------------
def get_entry_signal(df: pd.DataFrame):
    """
    Returns two identical values for backward compatibility
    (SIGNATURE INTACT)
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

    print("\n" + "=" * 50)
    print(f"{'PXY ENTRY ENGINE':^50}")
    print("=" * 50)
    print(f"{color_map.get(value1, Fore.YELLOW)}Signal: {value1}{Style.RESET_ALL}")
    print("=" * 50)


# -------------------- Self-test --------------------
if __name__ == "__main__":
    df = fetch_yf_data()

    if df is not None and not df.empty:
        df = calculate_supertrend(df)

    print_dashboard(df)

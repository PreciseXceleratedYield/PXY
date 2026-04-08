# sysentrpxy.py
import pandas as pd
from colorama import Fore, Style, init

from sysdtafpxy import fetch_yf_data
from syshkinpxy import detect_ha_flip_signal

init(autoreset=True)


# -------------------- Core ENTRY signal --------------------
def _compute_final_signal(df: pd.DataFrame) -> str:
    """
    Entry signal returns ATMBUY/ATMSELL/BULL/BEAR/NONE based on HA flips
    """
    if df is None or not all(col in df.columns for col in ['Open','High','Low','Close']):
        return NONE

    try:
        ha_signal, _, _, _ = detect_ha_flip_signal(df)

        if ha_signal == "BUY":
            return "ATMBUY"
        elif ha_signal == "SELL":
            return "ATMSELL"
        elif ha_signal == "BULL":
            return "BULL"
        elif ha_signal == "BEAR":
            return "BEAR"
        else:
            return NONE

    except Exception as e:
        print(f"[ERROR] HA Logic: {e}")
        return NONE


# -------------------- EXIT VALIDATION --------------------
def _validate_with_raw_direction(df: pd.DataFrame, entry_signal: str) -> str:
    """
    Converts entry signals into exit signals
    - ATMBUY -> BUY
    - ATMSELL -> SELL
    - BULL -> BULL
    - BEAR -> BEAR
    - None -> None
    """
    if entry_signal is None:
        return NONE

    mapping = {
        "ATMBUY": "BUY",
        "ATMSELL": "SELL",
        "BULL": "BULL",
        "BEAR": "BEAR"
    }

    return mapping.get(entry_signal, None)


# -------------------- Public function --------------------
def get_entry_signal(df: pd.DataFrame):
    entry = _compute_final_signal(df)
    exit_signal = _validate_with_raw_direction(df, entry)
    return entry, exit_signal


# -------------------- Terminal dashboard --------------------
def print_dashboard(df):
    entry, exit_signal = get_entry_signal(df)

    color_map = {
        "ATMBUY": Fore.GREEN, "BUY": Fore.GREEN,
        "ATMSELL": Fore.RED, "SELL": Fore.RED,
        "BULL": Fore.CYAN, "BEAR": Fore.MAGENTA,
        None: Fore.YELLOW
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
        print_dashboard(df)

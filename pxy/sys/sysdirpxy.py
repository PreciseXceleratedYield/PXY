# ==================================================
# SMA50 SLOPE ENGINE (5 vs 1 LOGIC)
# ==================================================

import pandas as pd
from sysdtafpxy import fetch_yf_data
from colorama import Fore, Style, init

init(autoreset=True)


# ==================================================
# CORE FUNCTION
# ==================================================
def get_sma50_slope(source_col="close", colored=False):
    """
    Logic:
    - Compute SMA(50)
    - Take last 6 SMA values
    - Compare avg(first 5) vs last (6th)

    Returns:
        "UP" / "DOWN" / "FLAT"
    """

    # 1️⃣ Fetch data (your existing pipeline)
    df = fetch_yf_data()

    if df is None or source_col not in df.columns:
        return None

    # 2️⃣ Compute SMA(50)
    sma50 = df[source_col].rolling(50).mean()

    # 3️⃣ Take last 6 values
    last6 = sma50.iloc[-6:]

    # Ensure valid values (no NaN)
    if last6.isna().any():
        return None

    # 4️⃣ Compute comparison
    avg_5 = last6.iloc[:5].mean()
    last  = last6.iloc[-1]

    # 5️⃣ Direction
    if last > avg_5:
        result = "UP"
    elif last < avg_5:
        result = "DOWN"
    else:
        result = "FLAT"

    # 6️⃣ Optional colored output
    if colored:
        if result == "UP":
            return Fore.GREEN + result + Style.RESET_ALL
        elif result == "DOWN":
            return Fore.RED + result + Style.RESET_ALL
        else:
            return Fore.YELLOW + result + Style.RESET_ALL

    return result


# ==================================================
# DIRECT RUN (OPTIONAL)
# ==================================================
if __name__ == "__main__":
    slope = get_sma50_slope(source_col="close", colored=True)
    print("SMA50 Slope:", slope)

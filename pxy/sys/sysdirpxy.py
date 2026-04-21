# ==================================================
# SMA50 SLOPE ENGINE (5 vs 1 + STRENGTH)
# ==================================================

import pandas as pd
from sysdtafpxy import fetch_yf_data
from colorama import Fore, Style, init

init(autoreset=True)


# ==================================================
# CORE FUNCTION
# ==================================================
def get_sma50_slope(source_col="close", colored=False, return_strength=False):
    """
    Logic:
    - Compute SMA(50)
    - Take last 6 SMA values
    - Compare avg(first 5) vs last (6th)

    Returns:
        Direction: "UP" / "DOWN" / "FLAT"
        Strength: slope_pct (optional)
    """

    # 1️⃣ Fetch data
    df = fetch_yf_data()

    if df is None or source_col not in df.columns:
        return (None, None) if return_strength else None

    # 2️⃣ Compute SMA(50)
    sma50 = df[source_col].rolling(50).mean()

    # 3️⃣ Take last 6 values
    last6 = sma50.iloc[-6:]

    if last6.isna().any():
        return (None, None) if return_strength else None

    # 4️⃣ Compute comparison
    avg_5 = last6.iloc[:5].mean()
    last  = last6.iloc[-1]

    # 5️⃣ Direction
    if last > avg_5:
        direction = "UP"
    elif last < avg_5:
        direction = "DOWN"
    else:
        direction = "FLAT"

    # 6️⃣ 🔥 Strength (normalized slope %)
    slope_pct = (last - avg_5) / avg_5 if avg_5 != 0 else 0

    # 7️⃣ Colored output (only for direction)
    if colored:
        if direction == "UP":
            direction_col = Fore.GREEN + direction + Style.RESET_ALL
        elif direction == "DOWN":
            direction_col = Fore.RED + direction + Style.RESET_ALL
        else:
            direction_col = Fore.YELLOW + direction + Style.RESET_ALL
    else:
        direction_col = direction

    # 8️⃣ Return
    if return_strength:
        return direction_col, slope_pct
    else:
        return direction_col


# ==================================================
# DIRECT RUN (OPTIONAL)
# ==================================================
if __name__ == "__main__":
    direction, strength = get_sma50_slope(return_strength=True, colored=True)
    print("SMA50 Slope:", direction)
    print("Strength   :", round(strength, 6) if strength is not None else "NA")

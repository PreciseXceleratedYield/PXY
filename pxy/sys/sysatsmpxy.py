# sysatsmpxy.py

import pandas as pd
from sysdtafpxy import fetch_yf_data
from syskatrpxy import calculate_atr
from colorama import Fore, Style, init

init(autoreset=True)


# -------------------- ATR → SMA PERIOD --------------------
def atr_to_period(atr_value: float) -> int:
    """
    ATR ≤ 8 → SMA = 5
    Every +2 ATR → reduce SMA by 1
    Range: 1 to 5
    """

    if atr_value <= 8:
        period = 5
    else:
        period = 5 - int((atr_value - 8) // 2)

    return max(1, min(5, period))


# -------------------- MAIN SIGNAL --------------------
def get_atr_sma(df: pd.DataFrame) -> dict:
    """
    Returns:
        atrsma : SMA value
        status : UP / DOWN / FLAT / NA
        period : dynamic SMA period
        atr    : latest ATR
    """

    if df is None or df.empty:
        return {"atrsma": 0, "status": "NA", "period": 0, "atr": 0}

    atr_series = calculate_atr(df)
    atr = atr_series.iloc[-1]

    if pd.isna(atr):
        return {"atrsma": 0, "status": "NA", "period": 0, "atr": 0}

    # -------- dynamic period --------
    period = atr_to_period(atr)

    # -------- SMA --------
    df['ATR_SMA'] = df['Close'].rolling(period).mean()
    sma = df['ATR_SMA'].iloc[-1]
    close = df['Close'].iloc[-1]

    if pd.isna(sma):
        return {"atrsma": 0, "status": "NA", "period": period, "atr": atr}

    # -------- STATUS --------
    if close > sma:
        status = "UP"
    elif close < sma:
        status = "DOWN"
    else:
        status = "FLAT"

    return {
        "atrsma": sma,
        "status": status,
        "period": period,
        "atr": atr
    }


# -------------------- SELF TEST --------------------
if __name__ == "__main__":
    df = fetch_yf_data()
    result = get_atr_sma(df)

    status = result["status"]
    sma_val = int(result["atrsma"])
    atr_val = round(result["atr"], 2)
    period = result["period"]

    # ---- COLOR ----
    if status == "UP":
        color = Fore.GREEN
    elif status == "DOWN":
        color = Fore.RED
    elif status == "FLAT":
        color = Fore.YELLOW
    else:
        color = Fore.WHITE

    # ---- OUTPUT ----
    left = f"ATR_SMA{period}:{status}"
    right = f"VAL:{sma_val}"
    line = f"{left:<21}{right:>21}"

    print(f"{color}{line}{Style.RESET_ALL}")

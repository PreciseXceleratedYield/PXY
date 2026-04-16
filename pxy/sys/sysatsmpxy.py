# sysatsmpxy.py

import pandas as pd
from sysdtafpxy import fetch_yf_data
from syskatrpxy import calculate_atr
from colorama import Fore, Style, init

init(autoreset=True)


# ==================================================
# 🔥 SINGLE SWITCH (SMART MODE)
# ==================================================
# "ATR" → ATR dynamic SMA logic
# number (e.g. 7, 9, 21) → SMA of that period
SMA_MODE = 9


# -------------------- ATR → SMA PERIOD --------------------
def atr_to_period(atr_value: float) -> int:
    if atr_value <= 8:
        period = 5
    else:
        period = 5 - int((atr_value - 8) // 2)

    return max(1, min(5, period))


# -------------------- MAIN SIGNAL --------------------
def get_atr_sma(df: pd.DataFrame) -> dict:

    if df is None or df.empty:
        return {"atrsma": 0, "status": "NA", "period": 0, "atr": 0}

    atr_series = calculate_atr(df)
    atr = atr_series.iloc[-1]

    if pd.isna(atr):
        return {"atrsma": 0, "status": "NA", "period": 0, "atr": 0}

    close = df['Close'].iloc[-1]

    # ==================================================
    # 🔥 MODE HANDLING
    # ==================================================
    if SMA_MODE == "ATR":
        period = atr_to_period(atr)
    else:
        period = int(SMA_MODE)

    df['SMA'] = df['Close'].rolling(period).mean()
    sma = df['SMA'].iloc[-1]

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

    color = Fore.GREEN if status == "UP" else Fore.RED if status == "DOWN" else Fore.YELLOW

    line = f"ATR_SMA{period}:{status}   VAL:{sma_val}   ATR:{atr_val}"
    print(f"{color}{line}{Style.RESET_ALL}")

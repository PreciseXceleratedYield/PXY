# sysatsmpxy.py

import pandas as pd
from sysdtafpxy import fetch_yf_data
from syskatrpxy import calculate_atr
from colorama import Fore, Style, init

init(autoreset=True)

TOTAL_WIDTH = 42


# -------------------- ATR → SMA PERIOD --------------------
def atr_to_period(atr_value: float) -> int:
    """
    ATR ≤ 8 → SMA = 5
    Every +2 ATR → reduce SMA by 1
    Final range: 1 to 5
    """

    if atr_value <= 8:
        period = 5
    else:
        period = 5 - int((atr_value - 8) // 2)

    return max(1, min(5, period))


# -------------------- SIGNAL ENGINE --------------------
def get_sma_atr_signal(df: pd.DataFrame) -> dict:
    """
    Returns:
        trend, sma, period, atr
    """

    if df is None or df.empty:
        return {"trend": "NA", "sma": 0, "period": 0, "atr": 0}

    atr_series = calculate_atr(df)
    atr = atr_series.iloc[-1]

    if pd.isna(atr):
        return {"trend": "NA", "sma": 0, "period": 0, "atr": 0}

    # -------- DYNAMIC PERIOD --------
    period = atr_to_period(atr)

    # -------- SMA --------
    df['SMA_ATR'] = df['Close'].rolling(period).mean()
    sma = df['SMA_ATR'].iloc[-1]
    close = df['Close'].iloc[-1]

    if pd.isna(sma):
        return {"trend": "NA", "sma": 0, "period": period, "atr": atr}

    # -------- TREND --------
    if close > sma:
        trend = "UP"
    elif close < sma:
        trend = "DOWN"
    else:
        trend = "FLAT"

    return {
        "trend": trend,
        "sma": sma,
        "period": period,
        "atr": atr
    }


# -------------------- SELF RUN DASHBOARD --------------------
if __name__ == "__main__":
    df = fetch_yf_data()
    result = get_sma_atr_signal(df)

    trend = result["trend"]
    sma_val = int(result["sma"])
    period = result["period"]
    atr_val = round(result["atr"], 2)

    # ---- COLOR ----
    if trend == "UP":
        color = Fore.GREEN
    elif trend == "DOWN":
        color = Fore.RED
    elif trend == "FLAT":
        color = Fore.YELLOW
    else:
        color = Fore.WHITE

    # ---- FORMAT (42 WIDTH DASHBOARD) ----
    left = f"SMA{period}:{trend}"
    right = f"ATR:{atr_val}"
    line = f"{left:<21}{right:>21}"

    print(f"{color}{line}{Style.RESET_ALL}")

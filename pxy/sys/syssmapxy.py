# sysatsmpxy.py

import pandas as pd
from sysdtafpxy import fetch_yf_data
from colorama import Fore, Style, init

init(autoreset=True)


# ==================================================
# 🔥 SIMPLE SMA ENGINE ONLY
# ==================================================
def get_sma(df: pd.DataFrame, period: int = 9) -> dict:
    """
    Simple SMA trend system
    """

    if df is None or df.empty:
        return {"value": 0, "status": "NA", "period": period}

    df['SMA'] = df['Close'].rolling(period).mean()
    sma = df['SMA'].iloc[-1]
    close = df['Close'].iloc[-1]

    if pd.isna(sma):
        return {"value": 0, "status": "NA", "period": period}

    if close > sma:
        status = "UP"
    elif close < sma:
        status = "DOWN"
    else:
        status = "FLAT"

    return {
        "value": sma,
        "status": status,
        "period": period
    }


# ==================================================
# 🔥 SELF TEST
# ==================================================
if __name__ == "__main__":
    df = fetch_yf_data()

    period = 9   # change this: 7, 21, 50 etc
    result = get_sma(df, period)

    color = {
        "UP": Fore.GREEN,
        "DOWN": Fore.RED,
        "FLAT": Fore.YELLOW,
        "NA": Fore.WHITE
    }.get(result["status"], Fore.WHITE)

    line = f"SMA({result['period']}): {result['status']} | VAL:{int(result['value'])}"
    print(f"{color}{line}{Style.RESET_ALL}")

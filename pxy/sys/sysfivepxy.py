# syssma5pxy.py

import pandas as pd
from sysdtafpxy import fetch_yf_data


# --------------------------------------------------
# FUNCTION
# --------------------------------------------------
def get_sma5_signal(df: pd.DataFrame) -> dict:
    """
    Returns SMA5 signal + value
    Output:
        {
            "trend": "UP/DOWN/FLAT/NA",
            "value": float
        }
    """

    if df is None or df.empty or len(df) < 5:
        return {"trend": "NA", "value": 0}

    df['SMA_5'] = df['Close'].rolling(window=5).mean()

    last = df.iloc[-1]
    sma = last['SMA_5']
    close = last['Close']

    if pd.isna(sma):
        return {"trend": "NA", "value": 0}

    if close > sma:
        trend = "UP"
    elif close < sma:
        trend = "DOWN"
    else:
        trend = "FLAT"

    return {"trend": trend, "value": sma}


# --------------------------------------------------
# SELF RUN (DASHBOARD STYLE)
# --------------------------------------------------
if __name__ == "__main__":
    from colorama import Fore, Style, init
    init(autoreset=True)

    df = fetch_yf_data()
    result = get_sma5_signal(df)

    trend = result["trend"]
    value = int(result["value"])

    # ---- COLOR ----
    if trend == "UP":
        color = Fore.GREEN
    elif trend == "DOWN":
        color = Fore.RED
    elif trend == "FLAT":
        color = Fore.YELLOW
    else:
        color = Fore.WHITE

    # ---- FORMAT (42 WIDTH SAME AS YOUR SYSTEM) ----
    left = f"SMA5:{trend}"
    right = f"VAL:{value}"
    line = f"{left:<21}{right:>21}"

    print(f"{color}{line}{Style.RESET_ALL}")

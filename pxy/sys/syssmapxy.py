import pandas as pd
from sysdtafpxy import fetch_yf_data
from syskatrpxy import calculate_atr  # Pulls ATR logic from your other file
from colorama import Fore, Style, init

init(autoreset=True)

# ================================================== #
# 🔥 ADAPTIVE SMA ENGINE
# ================================================== #
def get_sma(df: pd.DataFrame, period: int = 9) -> dict:
    """ 
    Adaptive SMA trend system. 
    Maintains original signature and return keys for downstream compatibility.
    Formula: 50 * (6 / ATR)
    """
    if df is None or df.empty:
        return {"value": 0, "status": "NA", "period": period}

    # 1. Get ATR and calculate adaptive period
    atr_series = calculate_atr(df)
    latest_atr = atr_series.iloc[-1]
    
    if not pd.isna(latest_atr) and latest_atr > 0:
        # Core Formula
        adaptive_period = int(round(50 * (6 / latest_atr)))
        
        # Safety: Ensure period is at least 2 and doesn't exceed available data
        period = max(2, min(adaptive_period, len(df)))

    # 2. Standard SMA Calculation using the new period
    df['SMA'] = df['Close'].rolling(period).mean()
    sma = df['SMA'].iloc[-1]
    close = df['Close'].iloc[-1]

    if pd.isna(sma):
        return {"value": 0, "status": "NA", "period": period}

    # 3. Trend Logic
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

# ================================================== #
# 🔥 SELF TEST
# ================================================== #
if __name__ == "__main__":
    df = fetch_yf_data()
    # 'period=9' is now just the default if ATR fails
    result = get_sma(df, period=9) 
    
    color = {
        "UP": Fore.GREEN,
        "DOWN": Fore.RED,
        "FLAT": Fore.YELLOW,
        "NA": Fore.WHITE
    }.get(result["status"], Fore.WHITE)
    
    line = f"SMA({result['period']}): {result['status']} | VAL:{int(result['value'])}"
    print(f"{color}{line}{Style.RESET_ALL}")


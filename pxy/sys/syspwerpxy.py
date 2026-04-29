# syspowrpxy.py
import pandas as pd
from sysdtafpxy import fetch_yf_data
from colorama import Fore, Style, init

init(autoreset=True)

# -------------------- Constants --------------------
ATR_PERIOD = 14
TOTAL_WIDTH = 42

def get_ce_pe_power(df=None):
    """
    Calculates CE/PE power using decimal-effective surgical logic:
    Power = ( (1 + ratio) * 100 ) - 100
    """
    if df is None:
        df = fetch_yf_data(period="2d", interval="1m")
    
    if df.empty or len(df) < 2:
        return "Flat", 1.0, 1.0 

    df = df[['Open','High','Low','Close']].astype(float).copy()

    # ATR calculation for volatility basis
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift(1)).abs()
    low_close = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr_val = tr.rolling(ATR_PERIOD, min_periods=1).mean().iloc[-1]

    # Detect the last price move
    last_move = float(df['Close'].iloc[-1] - df['Close'].iloc[-2])
    
    # --- SURGICAL POINT LOGIC (Effective Decimals) ---
    # We calculate the ratio of the move relative to ATR
    # Ratio 0.01 = 1 Point | Ratio 0.3 = 30 Points
    move_ratio = abs(last_move / atr_val) if atr_val > 0 else 0
    
    # Map to decimal (1.0 to 1.99)
    # This ensures the value never crosses 2.0
    effective_decimal = 1.0 + min(move_ratio, 0.99)

    # Convert to Points: (Value * 100) - 100
    pts = round((effective_decimal * 100) - 100, 1)
    pts = max(1.0, pts) # Floor at 1.0

    # Assign to respective side
    if last_move > 0:
        direction, CEPower, PEPower = "Up", pts, 1.0
    elif last_move < 0:
        direction, CEPower, PEPower = "Down", 1.0, pts
    else:
        direction, CEPower, PEPower = "Flat", 1.0, 1.0

    return direction, CEPower, PEPower

# -------------------- Test Output --------------------
if __name__ == "__main__":
    direction, CEPower, PEPower = get_ce_pe_power()
    
    ce_col = Fore.GREEN if CEPower > 1 else Fore.WHITE
    pe_col = Fore.RED if PEPower > 1 else Fore.WHITE

    # Prepare labels with 1-decimal precision
    l_txt = f"CE Power:{CEPower:.1f}"
    r_txt = f"PE Power:{PEPower:.1f}"
    
    # Calculate perfect spacing for width 42
    padding = " " * (TOTAL_WIDTH - len(l_txt) - len(r_txt))
    
    print(f"{ce_col}{l_txt}{Style.RESET_ALL}{padding}{pe_col}{r_txt}{Style.RESET_ALL}")


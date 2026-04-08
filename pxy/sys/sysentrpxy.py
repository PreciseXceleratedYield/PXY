# sysentrpxy.py
import pandas as pd
import pytz
from sysdtafpxy import fetch_yf_data

# Timezone
IST = pytz.timezone("Asia/Kolkata")

# -------------------- Deterministic Entry Signal --------------------
def get_entry_signal(df: pd.DataFrame):
    """
    Strict exclusive entry signal with no assumptions, without SuperTrend:
    - 08:55–09:15 IST → no signal
    - 09:16–09:26 IST → compare only last 2 candles (C1 vs C2), strict ATMBUY/ATMSELL
    - After 09:26 → compare last vs previous candle, strict ATMBUY/ATMSELL
    - Equal candles → no signal
    - No fallbacks anywhere
    """
    if df is None or len(df) < 2:
        return None, None

    df = df.copy()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert(IST)
    else:
        df.index = df.index.tz_convert(IST)

    now = df.index[-1].time()

    # -------------------- Morning Logic --------------------
    if now < pd.to_datetime("09:15").time():
        return None, None  # 08:55–09:15 → no signal
    elif pd.to_datetime("09:16").time() <= now <= pd.to_datetime("09:26").time():
        last_two = df['Close'].iloc[-2:]
        if last_two.iloc[-1] > last_two.iloc[-2]:
            return "ATMBUY", "BUY"
        elif last_two.iloc[-1] < last_two.iloc[-2]:
            return "ATMSELL", "SELL"
        else:
            return None, None  # equal → no signal

    # -------------------- After Morning → Normal Logic --------------------
    closes = df['Close']
    last_close = closes.iloc[-1]
    prev_close = closes.iloc[-2]

    # Strict exclusive signals
    if last_close > prev_close:
        return "ATMBUY", "BUY"
    elif last_close < prev_close:
        return "ATMSELL", "SELL"
    else:
        return None, None  # equal → no signal


# -------------------- Run if main --------------------
if __name__ == "__main__":
    # Fetch example data
    df = fetch_yf_data("NSE:TCS", period="1d", interval="1m")
    
    if df is not None and not df.empty:
        entry_signal, exit_signal = get_entry_signal(df)
        if entry_signal is None:
            print("No signal at this time.")
        else:
            print(f"Entry Signal: {entry_signal}, Exit Signal: {exit_signal}")

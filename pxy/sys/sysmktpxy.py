# ==================================================
# sysmktpxy.py  (PRODUCTION - CLEAN)
# ==================================================

from sysdtafpxy import fetch_yf_data


# ------------------------------
# Core 3-candle logic
# ------------------------------
def three_candle_signal(c1, c2, c3):
    if c2 < c1 and c2 < c3:
        return "BUY"
    elif c2 > c1 and c2 > c3:
        return "SELL"
    elif c1 < c2 < c3:
        return "BULL"
    elif c1 > c2 > c3:
        return "BEAR"
    else:
        return "NONE"


# ------------------------------
# Main Signal Function
# ------------------------------
def get_signal():
    try:
        df = fetch_yf_data(period="5d", interval="1m")

        # Safety checks
        if df is None or len(df) < 3:
            return "NONE", "NONE"

        # ---------- ENTRY (OHLC/4) ----------
        price = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

        p1 = price.iloc[-3]
        p2 = price.iloc[-2]
        p3 = price.iloc[-1]

        entry_signal = three_candle_signal(p1, p2, p3)

        # ---------- EXIT (CLOSE) ----------
        c1 = df['Close'].iloc[-3]
        c2 = df['Close'].iloc[-2]
        c3 = df['Close'].iloc[-1]

        exit_signal = three_candle_signal(c1, c2, c3)

        return entry_signal, exit_signal

    except Exception:
        # Fail-safe (never break your system)
        return "NONE", "NONE"


# ------------------------------
# OPTIONAL: Manual Run (No Debug Noise)
# ------------------------------
if __name__ == "__main__":
    entry, exit = get_signal()
    print(f"ENTRY: {entry} | EXIT: {exit}")

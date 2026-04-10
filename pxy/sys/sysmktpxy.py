# ==================================================
# sysmktpxy.py
# ==================================================

from sysdtafpxy import fetch_yf_data


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


def get_signal(df=None):
    try:
        # ✅ Use passed df if available
        if df is None:
            df = fetch_yf_data(period="5d", interval="1m")

        if df is None or len(df) < 3:
            return "NONE", "NONE"

        # ENTRY (OHLC/4)
        price = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        p1, p2, p3 = price.iloc[-3], price.iloc[-2], price.iloc[-1]
        entry_signal = three_candle_signal(p1, p2, p3)

        # EXIT (Close)
        c1, c2, c3 = df['Close'].iloc[-3], df['Close'].iloc[-2], df['Close'].iloc[-1]
        exit_signal = three_candle_signal(c1, c2, c3)

        return entry_signal, exit_signal

    except Exception:
        return "NONE", "NONE"


# ==================================================
# MAIN DEBUG RUN
# ==================================================
if __name__ == "__main__":
    print("\n================ DEBUG RUN ================\n")

    try:
        df = fetch_yf_data(period="5d", interval="1m")
        entry, exit_ = get_signal(df)

        print("[DEBUG] Data fetched OK")
        print(f"[DEBUG] Entry Signal: {entry}")
        print(f"[DEBUG] Exit  Signal: {exit_}")

    except Exception as e:
        print("[ERROR] Failed to run main block:", str(e))

    print("\n==========================================\n")

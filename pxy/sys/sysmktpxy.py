# ==================================================
# sysmktpxy.py (FINAL FIXED - PURE DF ENGINE)
# ==================================================

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


def get_signal(df):
    try:
        if df is None or len(df) < 3:
            return "NONE", "NONE"

        # ENTRY (OHLC avg)
        price = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        p1, p2, p3 = price.iloc[-3], price.iloc[-2], price.iloc[-1]
        entry_signal = three_candle_signal(p1, p2, p3)

        # EXIT (Close)
        c1, c2, c3 = df['Close'].iloc[-3], df['Close'].iloc[-2], df['Close'].iloc[-1]
        exit_signal = three_candle_signal(c1, c2, c3)

        print(f"[SIGNAL] ENTRY: {entry_signal} | EXIT: {exit_signal}")

        return entry_signal, exit_signal

    except Exception:
        return "NONE", "NONE"

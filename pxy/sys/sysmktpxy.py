# ==================================================
# sysmktpxy.py
# ==================================================

from sysdtafpxy import fetch_yf_data


# ==================================================
# 3-CANDLE LOGIC
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


# ==================================================
# DATA LOADER (NO INPUT REQUIRED)
# ==================================================
def get_df():
    df = fetch_yf_data(period="5d", interval="1m")

    if df is None or len(df) < 3:
        return None

    return df


# ==================================================
# MAIN SIGNAL ENGINE
# ==================================================
def get_signal():
    try:
        df = get_df()

        if df is None:
            return "NONE", "NONE"

        # ---------------- ENTRY (OHLC/4) ----------------
        price = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        p1, p2, p3 = price.iloc[-3], price.iloc[-2], price.iloc[-1]
        entry_signal = three_candle_signal(p1, p2, p3)

        # ---------------- EXIT (Close) ----------------
        c1, c2, c3 = df['Close'].iloc[-3], df['Close'].iloc[-2], df['Close'].iloc[-1]
        exit_signal = three_candle_signal(c1, c2, c3)

        # ==================================================
        # 🔥 ALIGNMENT LOGIC (ONLY FOR BULL / BEAR)
        # ==================================================
        if entry_signal == "BULL" and exit_signal == "BUY":
            entry_signal = "BUY"
        elif entry_signal == "BEAR" and exit_signal == "SELL":
            entry_signal = "SELL"

        return entry_signal, exit_signal

    except Exception as e:
        print(f"[ERROR] {e}")
        return "NONE", "NONE"


# ==================================================
# DEBUG RUN
# ==================================================
if __name__ == "__main__":

    print("\n================ DEBUG RUN ================\n")

    entry, exit_ = get_signal()

    print("[DEBUG] Data fetched OK")
    print(f"[DEBUG] Entry Signal: {entry}")
    print(f"[DEBUG] Exit  Signal: {exit_}")

    print("\n==========================================\n")

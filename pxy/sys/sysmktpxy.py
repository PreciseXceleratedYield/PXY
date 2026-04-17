# ==================================================
# PRO SIGNAL ENGINE
# ==================================================

from sysdtafpxy import fetch_yf_data


# ==================================================
# DATA LOADER
# ==================================================
def get_df():
    df = fetch_yf_data(period="5d", interval="1m")

    if df is None or len(df) < 4:
        return None

    return df


# ==================================================
# 3-CANDLE CORE SIGNAL
# ==================================================
def three_candle_signal(c1, c2, c3):

    # V / inverted V (highest priority)
    if c2 < c1 and c2 < c3:
        return "BUY"

    if c2 > c1 and c2 > c3:
        return "SELL"

    # trend
    if c1 < c2 < c3:
        return "BULL"

    if c1 > c2 > c3:
        return "BEAR"

    return "NONE"


# ==================================================
# 4-CANDLE STRUCTURE ENGINE (REAL, NO FAKE DATA)
# ==================================================
def four_candle_signal(c0, c1, c2, c3):

    # strong V / inverted V confirmation
    if c1 == min([c0, c1, c2, c3]):
        return "BUY"

    if c1 == max([c0, c1, c2, c3]):
        return "SELL"

    # strong trend continuation
    if c3 > c2 > c1 > c0:
        return "BULL"

    if c3 < c2 < c1 < c0:
        return "BEAR"

    return "NONE"


# ==================================================
# MOMENTUM ENGINE (LAST RESORT)
# ==================================================
def momentum_signal(c2, c3):

    if c3 > c2:
        return "BULL"
    elif c3 < c2:
        return "BEAR"
    else:
        return "NONE"


# ==================================================
# MASTER ENGINE (PRO FLOW CONTROL)
# ==================================================
def get_signal():
    try:
        df = get_df()

        if df is None:
            return "NONE", "NONE"

        # ==============================
        # ENTRY (OHLC4)
        # ==============================
        price = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        p0, p1, p2, p3 = price.iloc[-4], price.iloc[-3], price.iloc[-2], price.iloc[-1]

        entry_signal = three_candle_signal(p1, p2, p3)

        if entry_signal == "NONE":
            entry_signal = four_candle_signal(p0, p1, p2, p3)

        if entry_signal == "NONE":
            entry_signal = momentum_signal(p2, p3)

        # ==============================
        # EXIT (CLOSE)
        # ==============================
        c0, c1, c2, c3 = df['Close'].iloc[-4], df['Close'].iloc[-3], df['Close'].iloc[-2], df['Close'].iloc[-1]

        exit_signal = three_candle_signal(c1, c2, c3)

        if exit_signal == "NONE":
            exit_signal = four_candle_signal(c0, c1, c2, c3)

        if exit_signal == "NONE":
            exit_signal = momentum_signal(c2, c3)

        # ==============================
        # ALIGNMENT (SAFE UPGRADE ONLY)
        # ==============================
        if entry_signal == "BULL" and exit_signal == "BUY":
            entry_signal = "BUY"

        elif entry_signal == "BEAR" and exit_signal == "SELL":
            entry_signal = "SELL"

        return entry_signal, exit_signal

    except Exception as e:
        print(f"[ERROR] {e}")
        return "NONE", "NONE"


# ==================================================
# DEBUG
# ==================================================
if __name__ == "__main__":
    entry, exit_ = get_signal()

    print(entry, exit_)

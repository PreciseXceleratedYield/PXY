# ==================================================
# PRO SIGNAL ENGINE (WITH DEBUG MODE)
# ==================================================

from sysdtafpxy import fetch_yf_data
import pandas as pd

# ==================================================
# GLOBAL SWITCHES
# ==================================================
MODE = "HKIN"   # "OC2" or "HKIN"
DEBUG = False     # DEBUG SWITCH
EXIT_MODE = "C"   # "C" or "OHLC"   🔥 PATCH ADDED


# ==================================================
# DEBUG LOGGER
# ==================================================
def dbg(*args):
    if DEBUG:
        print("[DBG]", *args)


# ==================================================
# DATA LOADER
# ==================================================
def get_df():
    df = fetch_yf_data(period="5d", interval="1m")

    if df is None or len(df) < 4:
        dbg("Data insufficient")
        return None

    dbg("Data loaded:", len(df))
    return df


# ==================================================
# HEIKIN ASHI CALCULATOR (HKIN ONLY)
# ==================================================
def compute_heikin_ashi(df):
    ha = df.copy()

    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

    ha_open = [0] * len(df)
    ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2

    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i - 1] + ha_close.iloc[i - 1]) / 2

    ha_open = pd.Series(ha_open, index=df.index)

    ha['HA_Open'] = ha_open
    ha['HA_Close'] = ha_close

    dbg("Heikin Ashi computed")
    return ha


# ==================================================
# 3-CANDLE CORE SIGNAL
# ==================================================
def three_candle_signal(c1, c2, c3):

    dbg("3C:", c1, c2, c3)

    if c2 < c1 and c2 < c3:
        dbg("3C BUY")
        return "BUY"

    if c2 > c1 and c2 > c3:
        dbg("3C SELL")
        return "SELL"

    if c1 < c2 < c3:
        dbg("3C BULL")
        return "BULL"

    if c1 > c2 > c3:
        dbg("3C BEAR")
        return "BEAR"

    dbg("3C NONE")
    return "NONE"


# ==================================================
# 4-CANDLE STRUCTURE ENGINE
# ==================================================
def four_candle_signal(c0, c1, c2, c3):

    dbg("4C:", c0, c1, c2, c3)

    if c1 == min([c0, c1, c2, c3]):
        dbg("4C BUY")
        return "BUY"

    if c1 == max([c0, c1, c2, c3]):
        dbg("4C SELL")
        return "SELL"

    if c3 > c2 > c1 > c0:
        dbg("4C BULL")
        return "BULL"

    if c3 < c2 < c1 < c0:
        dbg("4C BEAR")
        return "BEAR"

    dbg("4C NONE")
    return "NONE"


# ==================================================
# MOMENTUM ENGINE
# ==================================================
def momentum_signal(c2, c3):

    dbg("MOM:", c2, c3)

    if c3 > c2:
        dbg("MOM BULL")
        return "BULL"
    elif c3 < c2:
        dbg("MOM BEAR")
        return "BEAR"
    else:
        dbg("MOM NONE")
        return "NONE"


# ==================================================
# HKIN ENTRY ENGINE (CLOSED CANDLES ONLY)
# ==================================================
def hkin_entry_signal(prev_o, prev_c, curr_o, curr_c):

    dbg("HKIN:", prev_o, prev_c, curr_o, curr_c)

    prev_green = prev_c > prev_o
    curr_green = curr_c > curr_o

    if (not prev_green) and curr_green:
        dbg("HKIN BUY")
        return "BUY"

    if prev_green and (not curr_green):
        dbg("HKIN SELL")
        return "SELL"

    if curr_green and prev_green:
        dbg("HKIN BULL")
        return "BULL"

    if (not curr_green) and (not prev_green):
        dbg("HKIN BEAR")
        return "BEAR"

    dbg("HKIN NONE")
    return "NONE"


# ==================================================
# MASTER ENGINE
# ==================================================
def get_signal():
    try:
        df = get_df()

        if df is None:
            return "NONE", "NONE"

        dbg("MODE:", MODE)

        # ==============================
        # OC2 MODE
        # ==============================
        if MODE == "OC2":

            price = (df['Open'] +  df['Close']) / 2
            p0, p1, p2, p3 = price.iloc[-4], price.iloc[-3], price.iloc[-2], price.iloc[-1]

            dbg("OC2 PRICE:", p0, p1, p2, p3)

            entry_signal = three_candle_signal(p1, p2, p3)

            if entry_signal == "NONE":
                entry_signal = four_candle_signal(p0, p1, p2, p3)

            if entry_signal == "NONE":
                entry_signal = momentum_signal(p2, p3)

        # ==============================
        # HKIN MODE
        # ==============================
        else:

            ha = compute_heikin_ashi(df)

            ha_o2 = ha['HA_Open'].iloc[-3]
            ha_c2 = ha['HA_Close'].iloc[-3]

            ha_o3 = ha['HA_Open'].iloc[-2]
            ha_c3 = ha['HA_Close'].iloc[-2]

            dbg("HKIN CLOSED:", ha_o2, ha_c2, ha_o3, ha_c3)

            entry_signal = hkin_entry_signal(ha_o2, ha_c2, ha_o3, ha_c3)

        # ==============================
        # EXIT (FIXED OHLC PATCH ONLY)
        # ==============================

        if EXIT_MODE == "C":

            c0, c1, c2, c3 = df['Close'].iloc[-4], df['Close'].iloc[-3], df['Close'].iloc[-2], df['Close'].iloc[-1]

            dbg("EXIT CLOSE:", c0, c1, c2, c3)

            exit_signal = three_candle_signal(c1, c2, c3)

            if exit_signal == "NONE":
                exit_signal = four_candle_signal(c0, c1, c2, c3)

            if exit_signal == "NONE":
                exit_signal = momentum_signal(c2, c3)

        else:

            h0, h1, h2, h3 = df['High'].iloc[-4], df['High'].iloc[-3], df['High'].iloc[-2], df['High'].iloc[-1]
            l0, l1, l2, l3 = df['Low'].iloc[-4], df['Low'].iloc[-3], df['Low'].iloc[-2], df['Low'].iloc[-1]

            dbg("EXIT OHLC:", h0, h1, h2, h3, l0, l1, l2, l3)

            # 🔥 FIXED + NO NONE BLOCK
            if l2 < l1 and l2 < l3 and h3 > h2:
                exit_signal = "BUY"

            elif h2 > h1 and h2 > h3 and l3 < l2:
                exit_signal = "SELL"

            elif h0 < h1 < h2 < h3 and l0 < l1 < l2 < l3:
                exit_signal = "BULL"

            elif h0 > h1 > h2 > h3 and l0 > l1 > l2 > l3:
                exit_signal = "BEAR"

            else:
                # 🔥 IMPORTANT: fallback to CLOSE instead of NONE
                c0, c1, c2, c3 = df['Close'].iloc[-4], df['Close'].iloc[-3], df['Close'].iloc[-2], df['Close'].iloc[-1]

                dbg("EXIT FALLBACK CLOSE:", c0, c1, c2, c3)

                exit_signal = three_candle_signal(c1, c2, c3)

                if exit_signal == "NONE":
                    exit_signal = four_candle_signal(c0, c1, c2, c3)

                if exit_signal == "NONE":
                    exit_signal = momentum_signal(c2, c3)

        dbg("FINAL ENTRY:", entry_signal, "EXIT:", exit_signal)

        # ==============================
        # ALIGNMENT
        # ==============================
        if entry_signal == "BULL" and exit_signal == "BUY":
            entry_signal = "BUY"

        elif entry_signal == "BEAR" and exit_signal == "SELL":
            entry_signal = "SELL"

        dbg("FINAL OUTPUT:", entry_signal, exit_signal)

        return entry_signal, exit_signal

    except Exception as e:
        print(f"[ERROR]", e)
        return "NONE", "NONE"


# ==================================================
# DEBUG RUN
# ==================================================
if __name__ == "__main__":
    entry, exit_ = get_signal()
    print(entry, exit_)

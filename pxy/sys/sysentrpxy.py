# ==================================================
# sysentrpxy.py (FINAL: ST + ADX + ATM/OTM LOGIC)
# ==================================================

from sysmktpxy import get_signal
from syshkinpxy import detect_ha_flip_signal
from sysstrndpxy import calculate_supertrend
from syssadxpxy import calculate_adx
from sysdtafpxy import fetch_yf_data


# ==================================================
# CORE ENGINE
# ==================================================
def get_entry_signal(df=None):

    # ------------------------------
    # BASE SIGNAL
    # ------------------------------
    signal, _ = get_signal()

    # EXIT = ALWAYS ORIGINAL SIGNAL
    exit_signal = signal

    # ------------------------------
    # PASS-THROUGH (NON TRADE SIGNALS)
    # ------------------------------
    if signal not in ["BUY", "SELL"]:
        print(f"[PASS] Signal (no filter): {signal}")
        return signal, exit_signal

    # ------------------------------
    # DEPTH
    # ------------------------------
    try:
        _, past_depth, _, _ = detect_ha_flip_signal()

        if past_depth == "NA":
            print("Depth: NA → NO TRADE")
            return "NONE", exit_signal

        side = past_depth[:2]   # CE / PE
        depth = int(past_depth[2:])

    except:
        return "NONE", exit_signal

    # ------------------------------
    # DATA FETCH
    # ------------------------------
    df = fetch_yf_data()

    # ------------------------------
    # SUPERTREND
    # ------------------------------
    df = calculate_supertrend(df)
    last = df.iloc[-1]

    trend = last["ST_Trend"]      # UP / DOWN
    st_line = int(last["ST"])

    # ------------------------------
    # ADX
    # ------------------------------
    adx = calculate_adx(df)

    if adx is None:
        print("[DEBUG] ADX = None → NO TRADE")
        return "NONE", exit_signal

    # Normalize ADX → 0 to 1
    adx_factor = min(max(adx / 50, 0), 1)

    # ------------------------------
    # DEPTH MODEL
    # ------------------------------
    # Trend-following → dynamic (1 to 6)
    trend_depth = int(round(6 - (adx_factor * 5)))
    trend_depth = min(max(trend_depth, 1), 6)

    # Counter → always strict
    counter_depth = 7

    # ------------------------------
    # REQUIREMENTS
    # ------------------------------
    if trend == "UP":
        buy_req = trend_depth      # trend-following BUY
        sell_req = counter_depth   # counter SELL
    else:
        buy_req = counter_depth
        sell_req = trend_depth

    # ------------------------------
    # PRINT
    # ------------------------------
    print(f"""
------------- SIMPLE (ST + ADX) -------------
Signal (RAW) : {signal}
Exit (RAW)   : {exit_signal}

Trend        : {trend}
ST Line      : {st_line}
ADX          : {round(adx, 2)}

Depth        : {side}{depth}

BUY Req      : >= {buy_req}
SELL Req     : >= {sell_req}
---------------------------------------------
""")

    # ------------------------------
    # ENTRY LOGIC (ATM / OTM)
    # ------------------------------
    if trend == "UP":

        # Trend-following BUY → ATM
        if signal == "BUY" and side == "PE" and depth >= buy_req:
            return "ATMBUY", exit_signal

        # Counter SELL → OTM
        if signal == "SELL" and side == "CE" and depth >= sell_req:
            return "OTMSELL", exit_signal

    elif trend == "DOWN":

        # Trend-following SELL → ATM
        if signal == "SELL" and side == "CE" and depth >= sell_req:
            return "ATMSELL", exit_signal

        # Counter BUY → OTM
        if signal == "BUY" and side == "PE" and depth >= buy_req:
            return "OTMBUY", exit_signal

    return "NONE", exit_signal


# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    entry, exit_signal = get_entry_signal()
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)

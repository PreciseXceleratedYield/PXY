# ==================================================
# sysentrpxy.py (FINAL: CLEAN PRINT + CE/PE REQ)
# ==================================================

from sysmktpxy import get_signal
from syshkinpxy import detect_ha_flip_signal
from sysstrndpxy import calculate_supertrend
from syssadxpxy import calculate_adx
from sysdtafpxy import fetch_yf_data


def get_entry_signal(df=None):

    # ------------------------------
    # BASE SIGNAL
    # ------------------------------
    signal, _ = get_signal()

    # EXIT = ALWAYS ORIGINAL SIGNAL
    exit_signal = signal

    # ------------------------------
    # DATA FETCH (single source)
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

    adx_factor = min(max(adx / 50, 0), 1)

    # ------------------------------
    # DEPTH MODEL
    # ------------------------------
    trend_depth = int(round(6 - (adx_factor * 5)))
    trend_depth = min(max(trend_depth, 1), 6)

    counter_depth = 7

    # ------------------------------
    # REQUIREMENTS (CE / PE view)
    # CE → SELL side, PE → BUY side
    # ------------------------------
    if trend == "UP":
        pe_req = trend_depth      # BUY (trend)
        ce_req = counter_depth    # SELL (counter)
    else:
        pe_req = counter_depth
        ce_req = trend_depth

    # ------------------------------
    # DEPTH (safe read)
    # ------------------------------
    try:
        _, past_depth, _, _ = detect_ha_flip_signal()

        if past_depth != "NA":
            side = past_depth[:2]
            depth = int(past_depth[2:])
        else:
            side = "NA"
            depth = 0

    except:
        side = "NA"
        depth = 0

    # ------------------------------
    # CLEAN PRINT (ALWAYS)
    # ------------------------------
    print(f"""
------------- SIMPLE (ST + ADX) -------------
Signal (RAW) : {signal}
Exit (RAW)   : {exit_signal}

Trend        : {trend}
ST Line      : {st_line}
ADX          : {round(adx, 2)}

Depth        : {side}{depth}

PE Req (BUY) : >= {pe_req}
CE Req (SELL): >= {ce_req}
---------------------------------------------
""")

    # ------------------------------
    # FILTER ONLY BUY / SELL
    # ------------------------------
    if signal not in ["BUY", "SELL"]:
        return signal, exit_signal

    # ------------------------------
    # ENTRY LOGIC (ATM / OTM)
    # ------------------------------
    if trend == "UP":

        if signal == "BUY" and side == "PE" and depth >= pe_req:
            return "ATMBUY", exit_signal

        if signal == "SELL" and side == "CE" and depth >= ce_req:
            return "OTMSELL", exit_signal

    elif trend == "DOWN":

        if signal == "SELL" and side == "CE" and depth >= ce_req:
            return "ATMSELL", exit_signal

        if signal == "BUY" and side == "PE" and depth >= pe_req:
            return "OTMBUY", exit_signal

    return "NONE", exit_signal


# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    entry, exit_signal = get_entry_signal()
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)

# ==================================================
# sysentrpxy.py (FINAL: INTEGRATED WITH sysmktpxy)
# ==================================================

from sysmktpxy import get_signal
from sysstrndpxy import calculate_supertrend
from syssadxpxy import calculate_adx
from sysdtafpxy import fetch_yf_data

from datetime import datetime, time
from zoneinfo import ZoneInfo


# ==================================================
# ENTRY ENGINE
# ==================================================
def get_entry_signal(df=None):

    # ------------------------------
    # BASE SIGNAL FROM sysmktpxy
    # ------------------------------
    entry_signal, exit_signal, ce, pe, last_opp, df, ha = get_signal()

    # ==============================
    # TIME BLOCK (IST)
    # ==============================
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_time = now.time()

    if time(9, 14) <= current_time < time(9, 16):
        print("[TIME BLOCK] NO TRADE")
        return "NONE", exit_signal

    if time(9, 16) <= current_time < time(9, 30):

        print("[MORNING BLOCK] DIRECT OTM MODE")

        if entry_signal == "BUY":
            return "OTMBUY", exit_signal

        if entry_signal == "SELL":
            return "OTMSELL", exit_signal

        return "NONE", exit_signal

    # ==============================
    # AFTER 09:30 FILTER ENGINE
    # ==============================

    df = fetch_yf_data()

    df = calculate_supertrend(df)
    last = df.iloc[-1]

    trend = last["ST_Trend"]
    st_line = int(last["ST"])

    adx = calculate_adx(df)

    if adx is None:
        return "NONE", exit_signal

    adx_factor = min(max(adx / 50, 0), 1)

    trend_depth = int(round(6 - (adx_factor * 5)))
    trend_depth = min(max(trend_depth, 1), 6)

    counter_depth = 7

    if trend == "UP":
        pe_req = trend_depth
        ce_req = counter_depth
    else:
        pe_req = counter_depth
        ce_req = trend_depth

    # ==============================
    # DEPTH FROM sysmktpxy
    # ==============================
    if entry_signal in ["BUY", "BULL"]:
        side = "CE"
        depth = ce
    elif entry_signal in ["SELL", "BEAR"]:
        side = "PE"
        depth = pe
    else:
        side = None
        depth = 0

    # ==============================
    # DEBUG PRINT
    # ==============================
    print(f"""
------------- ENGINE STATUS -------------
Signal      : {entry_signal}
Exit        : {exit_signal}

Trend       : {trend}
ST Line     : {st_line}
ADX         : {round(adx, 2)}

Depth Side  : {side}
Depth Value : {depth}
Last Opp    : {last_opp}

PE Req      : {pe_req}
CE Req      : {ce_req}
----------------------------------------
""")

    # ==============================
    # FILTER LOGIC
    # ==============================
    if entry_signal not in ["BUY", "SELL"]:
        return entry_signal, exit_signal

    if trend == "UP":

        if entry_signal == "BUY" and side == "CE" and depth >= ce_req:
            return "ATMBUY", exit_signal

        if entry_signal == "SELL" and side == "PE" and depth >= pe_req:
            return "OTMSELL", exit_signal

    elif trend == "DOWN":

        if entry_signal == "SELL" and side == "CE" and depth >= ce_req:
            return "ATMSELL", exit_signal

        if entry_signal == "BUY" and side == "PE" and depth >= pe_req:
            return "OTMBUY", exit_signal

    return "NONE", exit_signal


# ==================================================
# RUN
# ==================================================
if __name__ == "__main__":
    entry, exit_signal = get_entry_signal()
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)

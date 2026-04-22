# ==================================================
# sysentrpxy.py (FINAL: RAW PASS + FULL FILTER PIPELINE)
# ==================================================

from sysmktpxy import get_signal
from syshkinpxy import detect_ha_flip_signal
from sysstrndpxy import calculate_supertrend
from syssadxpxy import calculate_adx
from sysdtafpxy import fetch_yf_data

from datetime import datetime, time
from zoneinfo import ZoneInfo


# ==================================================
# DEPTH CONTROL SWITCH
# ==================================================
DEPTH_RELAXATION = 1   # 0 = strict, 1 = -1 relaxation, 2 = -2, etc.
MIN_DEPTH = 1


def get_entry_signal(df=None):

    # ------------------------------
    # BASE SIGNAL
    # ------------------------------
    signal, _ = get_signal()
    exit_signal = signal

    # ==================================================
    # 🔥 RAW PASS-THROUGH MODE (NO FILTERS)
    # ==================================================
    if signal in ["BULL", "BEAR", "NONE"]:
        print(f"🚧 🚧  NO ENTRY 🚧 🚧  AS 🚧 🚧  {signal} 🚧 🚧")
        return signal, exit_signal

    # ------------------------------
    # TIME BLOCK (IST)
    # ------------------------------
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_time = now.time()

    if time(9, 14) <= current_time < time(9, 16):
        print("[⏱️ ⌛] 09:14–09:16 → NO TRADE")
        return "NONE", exit_signal

    if time(9, 16) <= current_time < time(9, 30):
        print("[⏱️ ⌛] 09:16–09:30 → DIRECT OTM (NO FILTER)")

        if signal == "BUY":
            return "OTMBUY", exit_signal
        if signal == "SELL":
            return "OTMSELL", exit_signal

        return "NONE", exit_signal

    # ------------------------------
    # DATA FETCH
    # ------------------------------
    df = fetch_yf_data()

    df = calculate_supertrend(df)
    last = df.iloc[-1]

    trend = last["ST_Trend"]
    st_line = int(last["ST"])

    adx = calculate_adx(df)

    if adx is None:
        print("[DEBUG] ADX = None → NO TRADE")
        return "NONE", exit_signal

    adx_factor = min(max(adx / 50, 0), 1)

    trend_depth = int(round(6 - (adx_factor * 5)))
    trend_depth = min(max(trend_depth, 1), 6)

    counter_depth = 7

    # ------------------------------
    # REQUIREMENTS (WITH SWITCH)
    # ------------------------------
    if trend == "UP":
        pe_req = max(MIN_DEPTH, trend_depth - DEPTH_RELAXATION)
        ce_req = max(MIN_DEPTH, counter_depth - DEPTH_RELAXATION)
    else:
        pe_req = max(MIN_DEPTH, counter_depth - DEPTH_RELAXATION)
        ce_req = max(MIN_DEPTH, trend_depth - DEPTH_RELAXATION)

    # ------------------------------
    # DEPTH FETCH
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
    # MOMENTUM MODE
    # ------------------------------
    if depth > 7:

        if signal == "BUY":
            action = "ATMBUY"
        elif signal == "SELL":
            action = "ATMSELL"
        else:
            action = "NONE"

        print(f"{action} | SELL@CE{ce_req} | BUY@PE{pe_req}")
        return action, exit_signal

    # ------------------------------
    # ENTRY LOGIC
    # ------------------------------
    final_signal = "NONE"

    if trend == "UP":

        if signal == "BUY" and side == "PE" and depth >= pe_req:
            final_signal = "ATMBUY"

        if signal == "SELL" and side == "CE" and depth >= ce_req:
            final_signal = "OTMSELL"

    elif trend == "DOWN":

        if signal == "SELL" and side == "CE" and depth >= ce_req:
            final_signal = "ATMSELL"

        if signal == "BUY" and side == "PE" and depth >= pe_req:
            final_signal = "OTMBUY"

    # ------------------------------
    # FINAL PRINT
    # ------------------------------
    if signal == "BUY":
        action = "BUY"
    elif signal == "SELL":
        action = "SELL"
    elif signal == "OTMBUY":
        action = "ATMBUY"
    elif signal == "OTMSELL":
        action = "ATMSELL"
    else:
        action = signal

    print(f"🔓{signal}🔓 | {action} | REQ 🟢={ce_req} 🔴={pe_req} | 🔐 {side}{depth}")
    return final_signal, exit_signal


# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    entry, exit_signal = get_entry_signal()
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)

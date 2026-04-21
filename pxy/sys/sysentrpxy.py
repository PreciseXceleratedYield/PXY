# ==================================================
# sysentrpxy.py (SIMPLE + ADAPTIVE FINAL FIXED)
# ==================================================

from sysmktpxy import get_signal
from syshkinpxy import detect_ha_flip_signal
from sysdirpxy import get_sma50_slope
from syskatrpxy import calculate_dynamic_k
from sysdtafpxy import fetch_yf_data


# ==================================================
# MODE SWITCH
# ==================================================
MODE = "ADAPTIVE"   # "SIMPLE" or "ADAPTIVE"


# ==================================================
# CORE ENGINE
# ==================================================
def get_entry_signal(df=None):

    # ------------------------------
    # BASE SIGNAL
    # ------------------------------
    signal, exit_signal = get_signal()

    # ==================================================
    # SIMPLE MODE (UNCHANGED)
    # ==================================================
    if MODE == "SIMPLE":

        try:
            _, past_depth, _, _ = detect_ha_flip_signal()

            if past_depth == "NA":
                return "NONE", exit_signal

            side = past_depth[:2]
            depth = int(past_depth[2:])

        except:
            return "NONE", exit_signal

        if signal == "BUY" and side == "PE" and depth > 5:
            return "ATMBUY", exit_signal

        if signal == "SELL" and side == "CE" and depth > 5:
            return "ATMSELL", exit_signal

        return "NONE", exit_signal


    # ==================================================
    # ADAPTIVE MODE (FIXED SLOPE HANDLING)
    # ==================================================
    df = fetch_yf_data()

    try:
        _, past_depth, _, _ = detect_ha_flip_signal()

        if past_depth == "NA":
            return "NONE", exit_signal

        side = past_depth[:2]
        depth = int(past_depth[2:])

    except:
        return "NONE", exit_signal

    # ------------------------------
    # SLOPE + STRENGTH (FIXED)
    # ------------------------------
    slope, slope_pct = get_sma50_slope(return_strength=True)

    if slope is None:
        print("[DEBUG] SLOPE = None → NO TRADE")
        return "NONE", exit_signal

    # 🔥 normalize properly
    slope = str(slope).strip().upper()

    if "UP" in slope:
        slope = "UP"
    elif "DOWN" in slope:
        slope = "DOWN"

    if slope not in ["UP", "DOWN"]:
        print("[DEBUG] SLOPE INVALID →", slope)
        return "NONE", exit_signal

    # ------------------------------
    # SLOPE STRENGTH
    # ------------------------------
    slope_strength = 0
    if slope_pct is not None:
        slope_strength = min(abs(slope_pct) / 0.005, 1)

    slope_depth_factor = 1 - slope_strength

    # ------------------------------
    # VOLATILITY (K)
    # ------------------------------
    k = calculate_dynamic_k(df)
    k_norm = (k - 1) / 2

    # ------------------------------
    # PRESSURE
    # ------------------------------
    pressure = (0.5 * k_norm) + (0.5 * slope_depth_factor)

    # ------------------------------
    # DEPTH MODEL
    # ------------------------------

    trend_depth = int(round(1 + (1 - pressure) * 2))   # 1 → 3
    counter_depth = int(round(4 + pressure * 3))        # 4 → 7

    trend_depth = min(max(trend_depth, 1), 3)
    counter_depth = min(max(counter_depth, 4), 7)

    # ------------------------------
    # ENTRY LOGIC
    # ------------------------------
    if slope == "UP":

        if signal == "BUY" and side == "PE" and depth >= trend_depth:
            return "ATMBUY", exit_signal

        if signal == "SELL" and side == "CE" and depth >= counter_depth:
            return "ATMSELL", exit_signal

    elif slope == "DOWN":

        if signal == "SELL" and side == "CE" and depth >= trend_depth:
            return "ATMSELL", exit_signal

        if signal == "BUY" and side == "PE" and depth >= counter_depth:
            return "ATMBUY", exit_signal

    return "NONE", exit_signal


# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    entry, exit_signal = get_entry_signal()
    print("MODE:", MODE)
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)

# sys/exe/exetgtpxy_dashboard.py

import math
from colorama import init, Fore

init(autoreset=True)

# -------------------- SAFE HELPERS --------------------
def f(x, d=0.0):
    try:
        return float(x)
    except:
        return d


def i(x, d=0):
    try:
        return int(float(x))
    except:
        return d


# -------------------- MAIN ENGINE --------------------
def target_price(row):
    try:
        # 1️⃣ ENTRY (SAFE)
        entry = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry <= 0:
            print("INVALID_ENTRY|SKIP")
            return 0

        symbol = str(row.get("symbol", "UNKNOWN")).upper()

        # 2️⃣ SIGNAL (EXTERNAL)
        signal = str(row.get("signal", "NONE")).upper()

        # 3️⃣ INPUTS (SAFE)
        ce_p = f(row.get("ce_power", 1))
        pe_p = f(row.get("pe_power", 1))

        ce_d = i(row.get("hkin_ce_depth", 0))
        pe_d = i(row.get("hkin_pe_depth", 0))

        atr = f(row.get("atr", 0))
        katr = max(f(row.get("katr", 1)), 0.001)  # prevent divide-by-zero

        # 4️⃣ DYNAMIC POINT SYSTEM (ATR BASED)
        MIN_POINTS = max(int(atr / 5), 1)
        BASE_POINTS = max(int(atr), 1)
        MAX_POINTS = max(int(atr * 3), BASE_POINTS)

        # 5️⃣ CORE DIFFERENCES (DIRECTIONAL)
        power_diff = ce_p - pe_p
        depth_diff = ce_d - pe_d

        power_gap = abs(power_diff)
        depth_gap = abs(depth_diff)
        depth_strength = max(ce_d, pe_d)

        vol_ratio = atr / katr

        # 6️⃣ NORMALIZATION (SAFE BOUNDS)
        power_score = min(power_gap / 5, 1) * 6
        depth_score = min(depth_strength / 10, 1) * 5
        imbalance_score = min(depth_gap / 5, 1) * 3
        vol_score = min(vol_ratio / 3, 1) * 6

        # 7️⃣ MARKET BIAS (CE / PE)
        if power_diff > 0:
            bias = "CE"
        elif power_diff < 0:
            bias = "PE"
        else:
            bias = "NONE"

        # 8️⃣ SIGNAL SIDE
        if any(x in signal for x in ["BUY", "BULL"]):
            signal_side = "CE"
        elif any(x in signal for x in ["SELL", "BEAR"]):
            signal_side = "PE"
        else:
            signal_side = "NONE"

        # 9️⃣ ALIGNMENT LOGIC
        aligned = (
            (bias == signal_side) or
            (signal_side == "NONE") or
            (bias == "NONE")
        )

        # 🔟 SCORE + TARGET
        if not aligned:
            score = MIN_POINTS
            state = Fore.RED + "MIS" + Fore.RESET
            target = entry  # no move

        else:
            score = BASE_POINTS + power_score + depth_score + imbalance_score + vol_score
            score = int(max(MIN_POINTS, min(score, MAX_POINTS)))

            if bias == "CE":
                target = int(entry * (1 + score / 100))   # 📈 UP
                state = Fore.GREEN + "CE" + Fore.RESET

            elif bias == "PE":
                target = int(entry * (1 - score / 100))   # 📉 DOWN
                state = Fore.GREEN + "PE" + Fore.RESET

            else:
                target = entry
                state = Fore.YELLOW + "NONE" + Fore.RESET

        # 1️⃣1️⃣ CLEAN SYMBOL (REMOVE YEAR PREFIX LIKE 26)
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol

        # 1️⃣2️⃣ OUTPUT
        print(f"{clean_symbol} | {signal} | {bias} | E:{entry} | S:{score}% | {state} | T:{target}")

        return target

    except Exception as e:
        # absolute fallback safety
        print(f"ERROR|{str(e)}")
        return 0

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
        # 1️⃣ ENTRY
        entry = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry <= 0:
            print("INVALID_ENTRY|SKIP")
            return 0

        symbol = str(row.get("symbol", "UNKNOWN")).upper()

        # 2️⃣ EXIT SIGNAL (ONLY SOURCE OF DIRECTION)
        exit_signal = str(row.get("exit", "NONE")).upper()

        # 3️⃣ MULLU TREND
        mullu = str(row.get("mullu", "NONE")).upper()

        # 4️⃣ INPUTS
        ce_p = f(row.get("ce_power", 1))
        pe_p = f(row.get("pe_power", 1))

        ce_d = i(row.get("hkin_ce_depth", 0))
        pe_d = i(row.get("hkin_pe_depth", 0))

        atr = f(row.get("atr", 0))
        katr = max(f(row.get("katr", 1)), 0.001)

        # 5️⃣ POINT SYSTEM
        MIN_POINTS = max(int(atr), 1)
        BASE_POINTS = max(int(atr), 1)
        MAX_POINTS = max(int(atr * 3), BASE_POINTS)

        # 6️⃣ STRENGTH (NO DIRECTION HERE)
        power_gap = abs(ce_p - pe_p)
        depth_gap = abs(ce_d - pe_d)
        depth_strength = max(ce_d, pe_d)
        vol_ratio = atr / katr

        # 7️⃣ SCORES
        power_score = min(power_gap / 5, 1) * 6
        depth_score = min(depth_strength / 10, 1) * 5
        imbalance_score = min(depth_gap / 5, 1) * 3
        vol_score = min(vol_ratio / 3, 1) * 6

        # 8️⃣ ALIGNMENT & PHASE SELECTION
        power = 0
        depth = 0
        is_aligned = False
        direction = "NONE"

        if "CE" in symbol:
            power = ce_p
            depth = ce_d

            if "NONE" in exit_signal:
                is_aligned = True
                direction = "UP"

            else:
                is_aligned = (
                    (mullu == "UP") and
                    any(x in exit_signal for x in ["BUY", "BULL"])
                )
                direction = "UP"

        elif "PE" in symbol:
            power = pe_p
            depth = pe_d

            if "NONE" in exit_signal:
                is_aligned = True
                direction = "DOWN"

            else:
                is_aligned = (
                    (mullu == "DOWN") and
                    any(x in exit_signal for x in ["SELL", "BEAR"])
                )
                direction = "DOWN"

        # 9️⃣ SCORE + TARGET
        if not is_aligned:
            score = MIN_POINTS
            state = Fore.RED + "MIS" + Fore.RESET
            target = entry

        else:
            score = BASE_POINTS + power_score + depth_score + imbalance_score + vol_score
            score = int(max(MIN_POINTS, min(score, MAX_POINTS)))

            if direction == "UP":
                target = int(entry * (1 + score / 100))
                state = Fore.GREEN + "CE" + Fore.RESET

            elif direction == "DOWN":
                target = int(entry * (1 - score / 100))
                state = Fore.GREEN + "PE" + Fore.RESET

            else:
                target = entry
                state = Fore.YELLOW + "NONE" + Fore.RESET

        # 🔟 CLEAN SYMBOL
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol

        # 1️⃣1️⃣ OUTPUT
        print(f"{clean_symbol} | {exit_signal} | {mullu} | E:{entry} | S:{score}% | {state} | T:{target}")

        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0

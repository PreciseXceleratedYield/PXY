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

        # 2️⃣ INPUTS (SAFE)
        ce_p = f(row.get("ce_power", 1))
        pe_p = f(row.get("pe_power", 1))

        ce_d = i(row.get("hkin_ce_depth", 0))
        pe_d = i(row.get("hkin_pe_depth", 0))

        atr = f(row.get("atr", 0))
        katr = max(f(row.get("katr", 1)), 0.001)  # prevent divide-by-zero

        # 2.5️⃣ DYNAMIC POINT SYSTEM (ATR BASED)
        MIN_POINTS = max(int(atr / 10), 1)
        BASE_POINTS = max(int(atr), 1)
        MAX_POINTS = max(int(atr * 8), BASE_POINTS)

        # 3️⃣ CORE SIGNALS
        power_gap = abs(ce_p - pe_p)
        depth_gap = abs(ce_d - pe_d)
        depth_strength = max(ce_d, pe_d)
        vol_ratio = atr / katr

        # 4️⃣ NORMALIZATION (SAFE BOUNDS)
        power_score = min(power_gap / 5, 1) * 6
        depth_score = min(depth_strength / 10, 1) * 5
        imbalance_score = min(depth_gap / 5, 1) * 3
        vol_score = min(vol_ratio / 3, 1) * 6

        # 5️⃣ ALIGNMENT LOGIC (UPDATED)
        exit_signal = str(row.get("entry", "NONE")).upper()

        if "CE" in symbol:
            aligned = (
                any(x in exit_signal for x in ["BUY", "BULL"]) or
                "NONE" in exit_signal
            )

        elif "PE" in symbol:
            aligned = (
                any(x in exit_signal for x in ["SELL", "BEAR"]) or
                "NONE" in exit_signal
            )

        else:
            aligned = False

        # 6️⃣ SCORE
        if not aligned:
            score = MIN_POINTS
            state = Fore.RED + "MIS" + Fore.RESET
        else:
            score = BASE_POINTS + power_score + depth_score + imbalance_score + vol_score
            state = Fore.GREEN + "ALN" + Fore.RESET

        # 7️⃣ FINAL CLAMP (INTEGER ONLY)
        score = int(max(MIN_POINTS, min(score, MAX_POINTS)))

        # 8️⃣ TARGET (INTEGER ONLY)
        target = int(entry * (1 + score / 100))

        # 9️⃣ CLEAN SYMBOL (REMOVE YEAR PREFIX LIKE 26)
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol

        # 🔟 OUTPUT
        print(f"{clean_symbol} | E:{entry} | S:{score}% | {state} | T:{target}")

        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0

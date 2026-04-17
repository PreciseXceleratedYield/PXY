# sys/exe/exetgtpxy_dashboard.py

import math
from colorama import init

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

        # 2️⃣ INPUTS
        atr = f(row.get("atr", 0))

        # 3️⃣ MIN POINTS (ATR BASED)
        MIN_POINTS = max(int(atr / 15), 1)

        # 4️⃣ SIGNAL (STRICT MATCH)
        exit_signal = str(row.get("entry", "NONE")).upper()

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        bullish = exit_signal in ["BUY", "BULL"]
        bearish = exit_signal in ["SELL", "BEAR"]

        # 5️⃣ DEPTH INPUTS (MIN 1 ENFORCED)
        ce_depth = max(f(row.get("ce_depth", 1)), 1)
        pe_depth = max(f(row.get("pe_depth", 1)), 1)

        # 6️⃣ SCORE (EXCLUSIVE + EFFECTIVE)
        if is_ce and bullish:
            score = atr - ce_depth
            state = "CE✅"

        elif is_pe and bearish:
            score = atr - pe_depth
            state = "PE✅"

        else:
            score = MIN_POINTS
            state = "❌"

        # 7️⃣ SAFETY FLOOR
        score = max(score, 1.0)

        # 8️⃣ TARGET
        target = int(entry * (1 + score / 100))

        # 9️⃣ CLEAN SYMBOL
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol

        # 🔟 OUTPUT (AFTER ADJUSTMENT)
        print(f"{clean_symbol}|E:{entry:03d}|S:{int(score):02d}%|{'🟢' if (is_ce and bullish) else '🔴' if (is_pe and bearish) else '⚪'} |T:{target:03d}")

        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0

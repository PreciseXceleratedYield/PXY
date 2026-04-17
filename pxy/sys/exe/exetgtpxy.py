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

        # 4️⃣ SIGNAL
        exit_signal = str(row.get("entry", "NONE")).upper()

        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        bullish = any(x in exit_signal for x in ["BUY", "BULL", "NONE"])
        bearish = any(x in exit_signal for x in ["SELL", "BEAR", "NONE"])

        # 5️⃣ STRICT ALIGNMENT (NO NONE)
        aligned = (
            (is_ce and bullish) or
            (is_pe and bearish)
        )

        # 6️⃣ SCORE (EXCLUSIVE LOGIC)
        ce_depth = f(row.get("ce_depth", 0))
        pe_depth = f(row.get("pe_depth", 0))
        
        if is_ce and bullish:
            score = atr - ce_depth
            state = "CE✅"
        
        elif is_pe and bearish:
            score = atr - pe_depth
            state = "PE✅"
        
        else:
            score = atr
            state = "❌"
        
        # safety floor
        score = max(score, 1.0)

        # 7️⃣ TARGET
        target = int(entry * (1 + score / 100))

        # 8️⃣ CLEAN SYMBOL
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol

        # 9️⃣ OUTPUT
        print(f"{clean_symbol}|E:{entry}|S:{score}%|{state} |T:{target}")

        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0

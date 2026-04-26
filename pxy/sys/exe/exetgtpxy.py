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
        ce_power = f(row.get("ce_power", 0))
        pe_power = f(row.get("pe_power", 0))
        supertrend = row.get("supertrend", 0)

        # 🔥 FORCE (NEW ADDITION ONLY)
        ce_force = f(row.get("ce_force", 1.0))
        pe_force = f(row.get("pe_force", 1.0))

        # 3️⃣ OPTION TYPE
        is_ce = "CE" in symbol
        is_pe = "PE" in symbol

        # 4️⃣ SIGNALS
        entry_signal = str(row.get("entry", "NONE")).upper()
        exit_signal = str(row.get("exit", "NONE")).upper()
        counter = str(row.get("counter", "Y")).upper()

        # FIXED (minimal correction)
        _signal = exit_signal if counter == "Y" else entry_signal

        # -------------------- HLD MODE --------------------
        if _signal == "NONE":
            score = 6
            target = int(entry * (1 + score / 100))
            state = "🟡HLD"

            clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
            print(f"{clean_symbol}|| E:{entry:03d}|| S:{score:02d}%|| {state} || T:{target:03d}")

            return target

        bullish = any(x in _signal for x in ["BUY", "BULL", "UP"])
        bearish = any(x in _signal for x in ["SELL", "BEAR", "DOWN"])

        # 5️⃣ SUPER TREND DIRECTION (FIXED)
        st = str(supertrend).strip().upper()

        is_up = st == "UP"
        is_down = st == "DOWN"

        # -------------------- CORE LOGIC --------------------
        score = 0
        state = "❌"

        if is_up:
            # UP TREND
            if is_ce:
                score = atr * ce_power
                state = "UP_CE"
            elif is_pe:
                score = atr / 3
                state = "UP_PE"

        elif is_down:
            # DOWN TREND
            if is_pe:
                score = atr * pe_power
                state = "DOWN_PE"
            elif is_ce:
                score = atr / 3
                state = "DOWN_CE"

        # 🔥 FORCE BOOST (ONLY ADDITION)
        if is_ce:
            score = score * ce_force
        elif is_pe:
            score = score * pe_force

        # 7️⃣ TARGET
        target = int(entry * (1 + score / 100))

        # 8️⃣ CLEAN SYMBOL
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol

        # 9️⃣ OUTPUT
        print(f"{clean_symbol}|| E:{entry:03d}|| S:{int(score):02d}%|| {state} || T:{target:03d}")

        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0

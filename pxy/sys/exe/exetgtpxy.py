# sys/exe/exetgtpxy_dashboard.py

import math
from colorama import init, Fore

init(autoreset=True)

PRINT_DASHBOARD = False

# -------------------- CONFIG --------------------
MIN_POINTS = 3
BASE_POINTS = 5
MAX_POINTS = 20


# -------------------- SAFE HELPERS --------------------
def safe_float(x, default=0.0):
    try:
        return float(x)
    except:
        return default


def safe_int(x, default=0):
    try:
        return int(float(x))
    except:
        return default


# -------------------- MAIN ENGINE --------------------
def target_price(row):
    try:
        # 1️⃣ ENTRY
        entry = safe_float(row.get("pxy_entry") or row.get("buy_prc"))
        if entry <= 0:
            return 0

        symbol = str(row.get("symbol", "")).upper()

        # 2️⃣ SIGNALS
        ce_p = safe_float(row.get("ce_power", 1))
        pe_p = safe_float(row.get("pe_power", 1))

        ce_d = safe_int(row.get("hkin_ce_depth", 0))
        pe_d = safe_int(row.get("hkin_pe_depth", 0))

        atr = safe_float(row.get("atr", 0))
        katr = max(safe_float(row.get("katr", 1)), 0.001)

        # 3️⃣ RELATIVE CORE SIGNALS

        # Power imbalance (direction strength)
        power_gap = abs(ce_p - pe_p)

        # Dominance (who is stronger)
        dominant_power = max(ce_p, pe_p)

        # Depth maturity
        depth_strength = max(ce_d, pe_d)

        # Depth imbalance (trend clarity)
        depth_gap = abs(ce_d - pe_d)

        # Volatility expansion (ATR vs KATR)
        vol_ratio = atr / katr

        # normalize into stable ranges
        power_score = min(power_gap / 5, 1) * 6
        depth_score = min(depth_strength / 10, 1) * 5
        imbalance_score = min(depth_gap / 5, 1) * 3
        vol_score = min(vol_ratio / 3, 1) * 6

        # 4️⃣ ALIGNMENT (MISALIGN FILTER)
        aligned = (power_gap < 0.5) and (depth_gap <= 1)

        # 5️⃣ FINAL SCORE BUILD
        if not aligned:
            score = MIN_POINTS
        else:
            score = BASE_POINTS + power_score + depth_score + imbalance_score + vol_score

        # 6️⃣ SOFT LIMITS (NO JUMPING)
        score = max(MIN_POINTS, min(score, MAX_POINTS))

        # 7️⃣ FINAL TARGET (smooth % move)
        target = entry * (1 + score / 100)

        # 8️⃣ DEBUG
        if PRINT_DASHBOARD:
            print(f"{'-'*45}")
            print(f"{Fore.CYAN}SYMBOL   : {symbol}")
            print(f"{Fore.CYAN}ENTRY    : {entry}")
            print(f"{Fore.CYAN}CE/PE    : {ce_p} / {pe_p}")
            print(f"{Fore.CYAN}CE_D/PE_D: {ce_d} / {pe_d}")
            print(f"{Fore.CYAN}ATR/KATR : {atr} / {katr}")
            print(f"{Fore.YELLOW}POWER    : {power_score:.2f}")
            print(f"{Fore.YELLOW}DEPTH    : {depth_score:.2f}")
            print(f"{Fore.YELLOW}IMBAL    : {imbalance_score:.2f}")
            print(f"{Fore.YELLOW}VOL      : {vol_score:.2f}")
            print(f"{Fore.GREEN}SCORE %  : {score:.2f}")
            print(f"{Fore.GREEN}TARGET   : {round(target, 2)}")
            print(f"{'-'*45}\n")

        return round(target, 2)

    except Exception as e:
        print(f"Error target_price: {e}")
        return 0

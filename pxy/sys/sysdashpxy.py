# run_pyc.py
import runpy
import os
from colorama import Fore, Style, init
init(autoreset=True)

# ---- Pure Production Naming Alignment Imports ----
from sysdtafpxy import fetch_yf_data
from sysdthapxy import get_pxy_data
from sysdptpxy import detect_pxy_flip_signal
from syskatrpxy import calculate_atr, calculate_dynamic_k
from sysexitpxy import detect_raw_direction
from sysstrndpxy import calculate_supertrend
from syspwerpxy import get_ce_pe_power
from sysentrpxy import get_entry_signal
from syscseqpxy import get_candle_visual
from syscndlpxy import get_day_candle_bar
from sysbbospxy import get_bos_bar
from syssadxpxy import calculate_adx
from syssmapxy import get_sma          # ✅ SMA Tool Imported
from syscnfgpxy import SYSENTRPXY_SIGNAL_MODE

# ✅ KEEP CONSOLE ALIGNMENT
TOTAL_WIDTH = 42

# ---------------- STRUCTURAL UTILS ----------------
def safe_int(val):
    try:
        return 0 if val is None else int(float(val))
    except (ValueError, TypeError):
        return 0

# ================= RUN PYC FILES =================
def run_pyc_file():
    pyc_files = []
    for pyc_file in pyc_files:
        try:
            runpy.run_path(os.path.join(os.getcwd(), pyc_file), run_name="__main__")
        except Exception as e:
            print(f"Error running {pyc_file}: {e}")

# ================= CORE SNAPSHOT FUNCTION =================
def get_full_snapshot():
    result = {}
    master_df = fetch_yf_data()
    if master_df is None or master_df.empty:
        return None

    result["market_data_available"] = not master_df.attrs.get("data_fallback", False)
        
    # Enforce strict single source of truth across downstream layout components
    result["candle_visual"] = get_candle_visual(df=master_df)

    # ===== CLOSE MOMENTUM DATA ENGINE =====
    pxy_close, pxy_open, pxy_color, history_df = get_pxy_data(df=master_df)
    result["ha_close"] = pxy_close
    result["ha_open"] = pxy_open
    result["ha_color"] = pxy_color

    # ===== FLIP & TREND STREAK SIGNAL =====
    signal, past_depth, ce_depth, pe_depth = detect_pxy_flip_signal(df=master_df)
    if signal is None or signal == "NA":
        if not history_df.empty:
            signal = "BULL" if history_df['Close'].iloc[-1] > history_df['Open'].iloc[-1] else "BEAR"
        else:
            signal = "NONE"
    result["hkin_signal"] = signal
    result["hkin_past_depth"] = past_depth
    result["hkin_ce_depth"] = ce_depth
    result["hkin_pe_depth"] = pe_depth

    # ===== FORCE (ADX MATRIX) =====
    force_result = calculate_adx(master_df)
    if force_result:
        ce_force, pe_force = force_result
    else:
        ce_force, pe_force = 1.0, 1.0
    result["ce_force"] = ce_force
    result["pe_force"] = pe_force

    # ===== ATR & KATR MATRIX VOLATILITY =====
    atr_series = calculate_atr(master_df)
    atr_val = safe_int(atr_series.iloc[-1] if not atr_series.empty else 0)
    k_val = safe_int(calculate_dynamic_k(master_df))
    result["atr"] = atr_val
    result["katr"] = k_val

    # ===== PRICE & DIRECTION VECTORS =====
    price, direction = detect_raw_direction(master_df)
    result["price"] = safe_int(price)
    result["direction"] = direction if direction else "NONE"

    # ===== SUPERTREND PROFILES =====
    processed_st_df = calculate_supertrend(master_df.copy())
    trend = processed_st_df['ST_Trend'].iloc[-1] if not processed_st_df.empty else "NONE"
    line_val = safe_int(processed_st_df['ST'].iloc[-1] if not processed_st_df.empty else 0)
    result["supertrend"] = trend
    result["super_line"] = line_val
    result["df"] = processed_st_df

    # ===== DIRECTIONAL POWER MATRIX =====
    direction_power, ce, pe = get_ce_pe_power(df=master_df)
    result["direction_power"] = safe_int(direction_power)
    result["ce_power"] = safe_int(ce)
    result["pe_power"] = safe_int(pe)

    # ===== ENTRY ENGINE ROUTING =====
    entry, exit = get_entry_signal(master_df, mode=SYSENTRPXY_SIGNAL_MODE)
    result["entry"] = entry
    result["exit"] = exit

    # ===== DAY CANDLE DATA INTERFACE =====
    result["day_candle"] = get_day_candle_bar(master_df)

    # ===== BREAKOUT STRUCTURE (BOS) MATRIX =====
    bos_bar, _ = get_bos_bar(master_df)
    result["bos_bar"] = bos_bar if bos_bar else "NONE"
    
    # Calculate SMA 50 status (BULL/BEAR)
    sma_data = get_sma(master_df, period=50)
    result["sma"] = sma_data.get("status", "NA") # 🔄 RENAMED: Key is now 'sma'
    
    return result

# ================= PRINT DASHBOARD =================
def print_dashboard(data):
    if not data:
        print("No metrics fetched from data pipeline.")
        return

    # 1. CANDLE VISUAL STREAM
    print(data["candle_visual"])

    # 2. FLIP/TREND DATA LINE
    sig, pst = data["hkin_signal"], data["hkin_past_depth"]
    ce_d, pe_d = data["hkin_ce_depth"], data["hkin_pe_depth"]
    h_col = Fore.LIGHTGREEN_EX if sig in ["BUY","BULL"] else Fore.LIGHTRED_EX if sig in ["SELL","BEAR"] else Fore.YELLOW
    s1 = TOTAL_WIDTH - len(f"Hkin:{sig}") - len(f"Past:{pst}")
    print(Fore.WHITE + "Hkin:" + h_col + sig + " " * max(1, s1) + Fore.WHITE + "Past:" + h_col + str(pst))
    s2 = TOTAL_WIDTH - len(f"CE:{ce_d}") - len(f"PE:{pe_d}")
    print(Fore.WHITE + "CE:" + Fore.LIGHTGREEN_EX + str(ce_d) + " " * max(1, s2) + Fore.WHITE + "PE:" + Fore.LIGHTRED_EX + str(pe_d))

    # 3. FORCE PROFILES
    cef, pef = data.get("ce_force", 1.0), data.get("pe_force", 1.0)
    cef_c = Fore.LIGHTGREEN_EX if cef > 1 else Fore.CYAN
    pef_c = Fore.LIGHTRED_EX if pef > 1 else Fore.CYAN
    s_f = TOTAL_WIDTH - len(f"CE Force:{cef:.2f}") - len(f"PE Force:{pef:.2f}")
    print(Fore.WHITE + "CE Force:" + cef_c + f"{cef:.2f}" + " " * max(1, s_f) + Fore.WHITE + "PE Force:" + pef_c + f"{pef:.2f}")

    # 4. ATR SCALING BOUNDARIES
    atr, katr = data["atr"], data["katr"]
    s_a = TOTAL_WIDTH - len(f"ATR:{atr}") - len(f"KATR:{katr}")
    print(Fore.WHITE + "ATR:" + Fore.CYAN + str(atr) + " " * max(1, s_a) + Fore.WHITE + "KATR:" + Fore.CYAN + str(katr))

    # 5. MARKET PRICE INDEX
    prc, drct = data["price"], data["direction"]
    p_color = Fore.LIGHTGREEN_EX if drct=="UP" else Fore.LIGHTRED_EX if drct=="DOWN" else Fore.YELLOW
    s_p = TOTAL_WIDTH - len(f"Price:{prc}") - len(f"Mullu:{drct}")
    print(Fore.WHITE + "Price:" + Fore.CYAN + str(prc) + " " * max(1, s_p) + Fore.WHITE + "Mullu:" + p_color + drct)

    # 6. SUPERTREND ROUTING LINE
    trnd, line = data["supertrend"], data["super_line"]
    if trnd == "BUY": st_c = Fore.GREEN + Style.BRIGHT
    elif trnd == "SELL": st_c = Fore.RED + Style.BRIGHT
    elif trnd == "UP": st_c = Fore.LIGHTGREEN_EX
    elif trnd == "DOWN": st_c = Fore.LIGHTRED_EX
    else: st_c = Fore.YELLOW
    s_st = TOTAL_WIDTH - len(f"Super:{trnd}") - len(f"LINE:{line}")
    print(Fore.WHITE + "Super:" + st_c + trnd + " " * max(1, s_st) + Fore.WHITE + "LINE:" + Fore.CYAN + str(line))

    # 7. RISK METRIC DIRECTION POWER
    ce, pe = data["ce_power"], data["pe_power"]
    ce_c = Fore.LIGHTGREEN_EX if ce > pe else Fore.CYAN
    pe_c = Fore.LIGHTRED_EX if pe > ce else Fore.CYAN
    s_pw = TOTAL_WIDTH - len(f"CE Power:{ce}") - len(f"PE Power:{pe}")
    print(Fore.WHITE + "CE Power:" + ce_c + str(ce) + " " * max(1, s_pw) + Fore.WHITE + "PE Power:" + pe_c + str(pe))

    # 8. LIVE ORDER SIGNALS
    ent, ext = data["entry"], data["exit"]
    e_color = Fore.LIGHTGREEN_EX if "BUY" in ent or "UP" in ent else Fore.LIGHTRED_EX if "SELL" in ent or "DOWN" in ent else Fore.YELLOW
    s_e = TOTAL_WIDTH - len(f"Entry:{ent}") - len(f"Signal:{ext}")
    print(Fore.WHITE + "Entry:" + e_color + ent + " " * max(1, s_e) + Fore.WHITE + "Signal:" + e_color + ext)

    # 9. BOS BOUNDARY PRINT MATRIX & SURGICAL SMA ALIGNMENT LINE
    print(data["bos_bar"])
    
    # 🔄 RENAMED: Reading and printing from the 'sma' data key
    sma_status = data.get("sma", "NA")
    sma_color = Fore.LIGHTGREEN_EX if sma_status == "BULL" else Fore.LIGHTRED_EX if sma_status == "BEAR" else Fore.YELLOW
    s_sma = TOTAL_WIDTH - len("SMA:") - len(sma_status)
    print(Fore.WHITE + "SMA:" + " " * max(1, s_sma) + sma_color + sma_status)

# ================= MAIN RUNNER ENGINE =================
if __name__ == "__main__":
    run_pyc_file()
    snapshot_data = get_full_snapshot()
    print_dashboard(snapshot_data)

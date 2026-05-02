# run_pyc.py
import runpy
import os
from colorama import Fore, Style, init
init(autoreset=True)

# ---- Imports ----
from sysdtafpxy import fetch_yf_data
from sysdthapxy import get_ha_data
from syshkinpxy import detect_ha_flip_signal
from syskatrpxy import calculate_atr, calculate_dynamic_k
from sysexitpxy import detect_raw_direction
from sysstrndpxy import calculate_supertrend
from syspwerpxy import get_ce_pe_power
from sysentrpxy import get_entry_signal
from sysdeptpxy import get_candle_visual
from syscndlpxy import get_day_candle_bar
from sysbbospxy import get_bos_bar
from syssadxpxy import calculate_adx

# ✅ KEEP
TOTAL_WIDTH = 42

# ---------------- UTILS ----------------
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
    df = fetch_yf_data()
    if df is None or df.empty:
        return None
    
    result["df"] = df
    result["candle_visual"] = get_candle_visual(df=df)

    # ===== HAIKIN-ASHI =====
    ha_close, ha_open, ha_color, df = get_ha_data(df=df)
    result["ha_close"] = ha_close
    result["ha_open"] = ha_open
    result["ha_color"] = ha_color

    # ===== HAIKIN SIGNAL =====
    signal, past_depth, ce_depth, pe_depth = detect_ha_flip_signal(df=df)
    if signal is None:
        signal = "BULL" if df['HA_Close'].iloc[-1] > df['HA_Open'].iloc[-1] else "BEAR"
    result["hkin_signal"] = signal
    result["hkin_past_depth"] = past_depth
    result["hkin_ce_depth"] = ce_depth
    result["hkin_pe_depth"] = pe_depth

    # ===== FORCE =====
    force_result = calculate_adx(df)
    if force_result:
        ce_force, pe_force = force_result
    else:
        ce_force, pe_force = 1.0, 1.0
    result["ce_force"] = ce_force
    result["pe_force"] = pe_force

    # ===== ATR & KATR =====
    atr_series = calculate_atr(df)
    atr_val = safe_int(atr_series.iloc[-1] if not atr_series.empty else 0)
    k_val = safe_int(calculate_dynamic_k(df))
    result["atr"] = atr_val
    result["katr"] = k_val

    # ===== PRICE =====
    price, direction = detect_raw_direction(df)
    result["price"] = safe_int(price)
    result["direction"] = direction if direction else "NONE"

    # ===== SUPERTREND (MINER ONLY) =====
    df = calculate_supertrend(df)
    trend = df['ST_Trend'].iloc[-1] if not df.empty else "NONE"
    line_val = safe_int(df['ST'].iloc[-1] if not df.empty else 0)
    
    result["supertrend"] = trend
    result["super_line"] = line_val
    result["df"] = df

    # ===== POWER =====
    direction_power, ce, pe = get_ce_pe_power(df=df)
    result["direction_power"] = safe_int(direction_power)
    result["ce_power"] = safe_int(ce)
    result["pe_power"] = safe_int(pe)

    # ===== ENTRY SIGNAL =====
    entry, exit = get_entry_signal(df)
    result["entry"] = entry
    result["exit"] = exit

    # ===== DAY CANDLE =====
    result["day_candle"] = get_day_candle_bar(df)

    # ===== BOS =====
    bos_bar, bos_val = get_bos_bar(df)
    result["bos_bar"] = bos_bar if bos_bar else "NONE"
    result["bos_val"] = bos_val if bos_val else "NONE"

    return result

# ================= PRINT DASHBOARD =================
def print_dashboard(data):
    if not data:
        print("No data fetched.")
        return

    # Header Separator
    print(Fore.CYAN + "═" * TOTAL_WIDTH)

    # ===== CANDLE VISUAL =====
    print(data["candle_visual"])

    # ===== HAIKIN & PRICE BLOCK =====
    signal = data["hkin_signal"]
    past = data["hkin_past_depth"]
    h_col = Fore.GREEN if signal in ["BUY","BULL"] else Fore.RED if signal in ["SELL","BEAR"] else Fore.YELLOW
    
    price = data["price"]
    direction = data["direction"]
    p_col = Fore.GREEN if direction=="UP" else Fore.RED if direction=="DOWN" else Fore.YELLOW
    
    # Surgical Layout 1
    print(f"{Fore.YELLOW}HKIN: {h_col}{signal:<8} {Fore.YELLOW}PST: {h_col}{past:>2} {Fore.CYAN}│ {Fore.YELLOW}PRC: {p_col}{price}")

    # ===== FORCE & ATR BLOCK =====
    ce_f, pe_f = data.get("ce_force", 1.0), data.get("pe_force", 1.0)
    atr, katr = data["atr"], data["katr"]
    print(f"{Fore.YELLOW}FORC: {Fore.GREEN}{ce_f:.1f}{Fore.WHITE}/{Fore.RED}{pe_f:.1f}  {Fore.CYAN}│ {Fore.YELLOW}ATR: {Fore.WHITE}{atr:<4} {Fore.YELLOW}K: {Fore.CYAN}{katr}")

    # ===== SUPERTREND (MINER FOCUS) =====
    trend = data["supertrend"]
    line = data["super_line"]
    st_col = Fore.GREEN if trend in ["UP", "BUY"] else Fore.RED if trend in ["DOWN", "SELL"] else Fore.YELLOW
    
    # "LINE" gets white for visibility, "Super" gets surgical color
    print(f"{Fore.YELLOW}SUPER: {st_col}{trend:<7} {Fore.CYAN}│ {Fore.YELLOW}LINE: {Fore.WHITE}{line}")

    # ===== POWER BLOCK =====
    ce, pe = data["ce_power"], data["pe_power"]
    ce_p_col = Fore.GREEN if ce > pe else Fore.RED if ce < pe else Fore.YELLOW
    pe_p_col = Fore.GREEN if pe > ce else Fore.RED if pe < ce else Fore.YELLOW
    print(f"{Fore.YELLOW}PWR-CE: {ce_p_col}{ce:<4} {Fore.YELLOW}PWR-PE: {pe_p_col}{pe:>4}")

    # ===== ENTRY & SIGNAL BLOCK =====
    entry = data["entry"]
    exit = data["exit"]
    e_col = (Fore.GREEN if entry in ["ATMBUY","OTMBUY","SBUY","BBUY","RBUY"] else Fore.RED if entry in ["ATMSELL","OTMSELL","SSELL","BSELL","RSELL"] else Fore.YELLOW)
    
    print(f"{Fore.CYAN}─" * TOTAL_WIDTH)
    print(f"{Fore.YELLOW}ENTRY: {e_col}{entry:<12} {Fore.YELLOW}SIG: {e_col}{exit}")

    # ===== BOS & DAY CANDLE =====
    print(data["bos_bar"])
    print(Fore.CYAN + "═" * TOTAL_WIDTH)

# ================= MAIN =================
if __name__ == "__main__":
    run_pyc_file()
    data = get_full_snapshot()
    print_dashboard(data)


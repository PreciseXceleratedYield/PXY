# sysdashpxy.py
import runpy
import os
from colorama import Fore, Style, init

init(autoreset=True)

# ---- Imports ----
from sysdtafpxy import fetch_yf_data
from sysdthapxy import get_ha_data
from sysmktpxy import detect_ha_flip_signal  # for final candle engine
from sysstrhpxy import get_candle_strength_line
from syskatrpxy import calculate_atr, calculate_dynamic_k
from sysexitpxy import detect_raw_direction
from sysstrndpxy import calculate_supertrend
from syspwerpxy import get_ce_pe_power
from sysentrpxy import get_entry_signal
from sysdeptpxy import get_candle_visual
from syscndlpxy import get_day_candle_bar
from sysbbospxy import get_bos_bar

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

    # --- Fetch raw data once
    df_raw = fetch_yf_data()
    if df_raw is None or df_raw.empty:
        return None
    result["df"] = df_raw.copy()

    # --- Ensure OHLC columns exist for calculations ---
    for col in ['Open', 'High', 'Low', 'Close']:
        if col not in df_raw.columns:
            df_raw[col] = df_raw['Close']  # fallback

    # --- Candle visual ---
    df = df_raw.copy()
    result["candle_visual"] = get_candle_visual(df=df)

    # ===== FINAL CANDLE ENGINE =====
    signal, past_depth, ce_depth, pe_depth = detect_ha_flip_signal(df=df)
    result["mode"] = "HACV"  # or dynamically detect
    result["signal"] = signal
    result["past"] = past_depth
    result["ce"] = ce_depth
    result["pe"] = pe_depth

    # ===== HAIKIN-ASHI =====
    ha_close, ha_open, ha_color, _ = get_ha_data(df=df)
    result["ha_close"] = ha_close
    result["ha_open"] = ha_open
    result["ha_color"] = ha_color

    # ===== STRENGTH =====
    line, _, _ = get_candle_strength_line(df=df)
    result["strength_line"] = line

    # ===== ATR & KATR =====
    try:
        atr_series = calculate_atr(df_raw)
        atr_val = safe_int(atr_series.iloc[-1] if not atr_series.empty else 0)
    except Exception:
        atr_val = 0
    try:
        k_val = safe_int(calculate_dynamic_k(df_raw))
    except Exception:
        k_val = 0
    result["atr"] = atr_val
    result["katr"] = k_val

    # ===== PRICE =====
    try:
        price, direction = detect_raw_direction(df_raw)
        result["price"] = safe_int(price)
        result["direction"] = direction if direction else "NONE"
    except Exception:
        result["price"] = 0
        result["direction"] = "NONE"

    # ===== SUPERTREND =====
    try:
        df_st = calculate_supertrend(df_raw)
        trend = df_st['ST_Trend'].iloc[-1] if not df_st.empty else "NONE"
        line_val = safe_int(df_st['ST'].iloc[-1] if not df_st.empty else 0)
        result["supertrend"] = trend
        result["super_line"] = line_val
        result["df"] = df_st
    except Exception:
        df_st = df_raw.copy()
        result["supertrend"] = "NONE"
        result["super_line"] = 0

    # ===== POWER =====
    try:
        direction_power, ce, pe = get_ce_pe_power(df=df_st)
        result["direction_power"] = safe_int(direction_power)
        result["ce_power"] = safe_int(ce)
        result["pe_power"] = safe_int(pe)
    except Exception:
        result["direction_power"] = result["ce_power"] = result["pe_power"] = 0

    # ===== ENTRY SIGNAL =====
    try:
        entry, reversal = get_entry_signal(df_st)
        if entry is None or entry == "NONE":
            last_close = df_st['Close'].iloc[-1]
            st_value = df_st['ST'].iloc[-1] if 'ST' in df_st.columns else last_close
            if last_close > st_value:
                entry = "ATMBUY"
                reversal = "SBUY"
            else:
                entry = "ATMSELL"
                reversal = "SSELL"
        result["entry"] = entry
        result["reversal"] = reversal
    except Exception:
        result["entry"] = "NONE"
        result["reversal"] = "NONE"

    # ===== DAY CANDLE =====
    try:
        result["day_candle"] = get_day_candle_bar(df_st)
    except Exception:
        result["day_candle"] = ""

    # ===== BOS =====
    try:
        bos_bar, bos_val = get_bos_bar(df_st)
        result["bos_bar"] = bos_bar if bos_bar else "NONE"
        result["bos_val"] = bos_val if bos_val else "NONE"
    except Exception:
        result["bos_bar"] = "NONE"
        result["bos_val"] = "NONE"

    return result

# ================= PRINT DASHBOARD =================
def print_dashboard(data):
    if not data:
        print("No data fetched.")
        return

    # ===== CANDLE VISUAL =====
    print(data["candle_visual"])

    # ===== FINAL CANDLE ENGINE LINE =====
    mode = data.get("mode", "HACV")
    signal = data.get("signal", "NONE")
    past = data.get("past", 1)
    ce = data.get("ce", 1)
    pe = data.get("pe", 1)
    print(f"Mode: {mode}  Signal: {signal}  Past: {past}  CE: {ce}  PE: {pe}")

    # ===== STRENGTH =====
    print(data["strength_line"])

    # ===== ATR =====
    atr_val = data["atr"]
    k_val = data["katr"]
    space = TOTAL_WIDTH - len(f"ATR:{atr_val}") - len(f"KATR:{k_val}")
    print(Fore.YELLOW + "ATR:" + Fore.WHITE + str(atr_val) + " " * space + Fore.YELLOW + "KATR:" + Fore.CYAN + str(k_val))

    # ===== PRICE =====
    price = data["price"]
    direction = data["direction"]
    color = Fore.GREEN if direction=="UP" else Fore.RED if direction=="DOWN" else Fore.YELLOW
    space = TOTAL_WIDTH - len(f"Price:{price}") - len(f"Mullu:{direction}")
    print(Fore.YELLOW + "Price:" + color + str(price) + " " * space + Fore.YELLOW + "Mullu:" + color +direction)

    # ===== SUPERTREND =====
    trend = data["supertrend"]
    line_val = data["super_line"]
    color = Fore.GREEN if trend=="UP" else Fore.RED if trend=="DOWN" else Fore.YELLOW
    space = TOTAL_WIDTH - len(f"Super:{trend}") - len(f"LINE:{line_val}")
    print(Fore.YELLOW + "Super:" + color +trend + " " * space + Fore.YELLOW + "LINE:" + color + str(line_val))

    # ===== POWER =====
    ce_power = data["ce_power"]
    pe_power = data["pe_power"]
    ce_color = Fore.GREEN if ce_power > pe_power else Fore.RED if ce_power < pe_power else Fore.YELLOW
    pe_color = Fore.GREEN if pe_power > ce_power else Fore.RED if pe_power < ce_power else Fore.YELLOW
    space = TOTAL_WIDTH - len(f"CE Power:{ce_power}") - len(f"PE Power:{pe_power}")
    print(Fore.YELLOW + "CE Power:" + ce_color + str(ce_power) + " " * space + Fore.YELLOW + "PE Power:" + pe_color + str(pe_power))

    # ===== ENTRY =====
    entry = data["entry"]
    reversal = data["reversal"]
    color = (
        Fore.GREEN if entry in ["ATMBUY","OTMBUY","SBUY","BBUY","RBUY"]
        else Fore.RED if entry in ["ATMSELL","OTMSELL","SSELL","BSELL","RSELL"]
        else Fore.YELLOW
    )
    space = TOTAL_WIDTH - len(f"Entry:{entry}") - len(f"Signal:{reversal}")
    print(Fore.YELLOW + "Entry:" + color + entry + " " * space + Fore.YELLOW + "Signal:" + color + reversal)

    # ===== DAY CANDLE & BOS =====
    if data.get("day_candle"):
        print(data["day_candle"])
    print(data["bos_bar"])

# ================= MAIN =================
if __name__ == "__main__":
    run_pyc_file()
    data = get_full_snapshot()
    print_dashboard(data)

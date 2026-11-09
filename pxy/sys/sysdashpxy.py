# run_pyc.py
import runpy
import os
import pandas as pd
from colorama import Fore, Style, init
init(autoreset=True)

# ---- Pure Production Naming Alignment Imports ----
from sysdtafpxy import fetch_yf_data, fetch_yf_data_for_monitor
from syscnfgpxy import (
    SYSDTAFPXY_DEFAULT_TARGET_ROWS,
    SYSDTAFPXY_YAHOO_MAX_AGE_SECONDS,
    SYSCNFGPXY_MARKET_OPEN,
    SYSCNFGPXY_TIMEZONE,
    SYSCNFGPXY_TRADING_DAY_END,
    SYSSTRNDPXY_CHART_TARGET_ROWS,
)
from sysdthapxy import get_pxy_data, get_signal_depth_analysis
from syskatrpxy import calculate_atr, calculate_dynamic_k
from sysexitpxy import detect_raw_direction
from sysictrpxy import calculate_indicators, get_indicator_signals
from syspwerpxy import get_ce_pe_power
from sysentrpxy import get_entry_signal
from sysoutpxy import get_out_candles
from syscseqpxy import get_candle_visual
from syscndlpxy import get_day_candle_bar
from sysbbospxy import get_bos_bar
from syssadxpxy import calculate_adx

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
def get_full_snapshot(monitor=False):
    result = {}
    data_fetch = fetch_yf_data_for_monitor if monitor else fetch_yf_data
    chart_source_df = data_fetch(target_rows=SYSSTRNDPXY_CHART_TARGET_ROWS)
    if chart_source_df is None or chart_source_df.empty:
        return None

    master_df = chart_source_df.tail(SYSDTAFPXY_DEFAULT_TARGET_ROWS).copy()
    is_futures_fallback = bool(master_df.attrs.get("data_fallback", False))
    result["market_data_available"] = not is_futures_fallback

    # Yahoo timestamps are candle-start times. Measure the age in configured
    # IST; this is warning-only and deliberately does not gate any signal.
    candle_timestamp = pd.Timestamp(master_df.index[-1])
    if candle_timestamp.tzinfo is None:
        candle_timestamp = candle_timestamp.tz_localize("UTC")
    candle_timestamp = candle_timestamp.tz_convert(SYSCNFGPXY_TIMEZONE)
    now_timestamp = pd.Timestamp.now(tz=SYSCNFGPXY_TIMEZONE)
    candle_age_seconds = (
        now_timestamp - candle_timestamp
    ).total_seconds()
    market_time = now_timestamp.time()
    is_exchange_session = (
        now_timestamp.weekday() < 5
        and SYSCNFGPXY_MARKET_OPEN
        <= market_time
        < SYSCNFGPXY_TRADING_DAY_END
    )
    candle_is_stale = (
        is_exchange_session
        and not is_futures_fallback
        and (
            candle_age_seconds < 0
            or candle_age_seconds > SYSDTAFPXY_YAHOO_MAX_AGE_SECONDS
        )
    )
    result["market_data_timestamp"] = candle_timestamp.isoformat()
    result["market_data_age_seconds"] = round(candle_age_seconds, 1)
    result["market_data_stale"] = bool(candle_is_stale)

    # Enforce strict single source of truth across downstream layout components
    result["candle_visual"] = get_candle_visual(df=master_df)

    # ===== CLOSE MOMENTUM DATA ENGINE =====
    pxy_close, pxy_open, pxy_color, _ = get_pxy_data(df=master_df)
    result["ha_close"] = pxy_close
    result["ha_open"] = pxy_open
    result["ha_color"] = pxy_color

    # ===== FLIP & TREND STREAK SIGNAL =====
    signal_depth = get_signal_depth_analysis(df=master_df)
    result["hkin_signal"] = signal_depth["signal"]
    result["hkin_past_depth"] = signal_depth["past_depth"]
    result["hkin_ce_depth"] = signal_depth["ce_depth"]
    result["hkin_pe_depth"] = signal_depth["pe_depth"]
    result["hkin_signal_time"] = signal_depth["signal_candle_time"]

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
    processed_st_df = calculate_indicators(master_df.copy())
    chart_df = calculate_indicators(chart_source_df.copy())
    out_chart_source_df = get_out_candles(chart_source_df.copy())
    out_chart_df = calculate_indicators(out_chart_source_df.copy())
    trend = chart_df['ST_Trend'].iloc[-1] if not chart_df.empty else "NONE"
    line_val = safe_int(chart_df['ST'].iloc[-1] if not chart_df.empty else 0)
    result["supertrend"] = trend
    result["super_line"] = line_val
    indicator_signals = get_indicator_signals(processed_st_df)
    result["sma"] = indicator_signals["sma"]
    result["tsma"] = indicator_signals["tsma"]
    result["df"] = processed_st_df
    # The web chart displays OUT-mode candles; entry routing keeps raw candles.
    result["chart_df"] = out_chart_df

    # ===== DIRECTIONAL POWER MATRIX =====
    direction_power, ce, pe = get_ce_pe_power(df=master_df)
    result["direction_power"] = safe_int(direction_power)
    result["ce_power"] = safe_int(ce)
    result["pe_power"] = safe_int(pe)

    # ===== ENTRY ENGINE ROUTING =====
    entry, exit = get_entry_signal(
        master_df,
        processed_supertrend=chart_df,
    )
    result["entry"] = entry
    result["exit"] = exit

    # ===== DAY CANDLE DATA INTERFACE =====
    result["day_candle"] = get_day_candle_bar(master_df)

    # ===== BREAKOUT STRUCTURE (BOS) MATRIX =====
    bos_bar, _ = get_bos_bar(master_df)
    result["bos_bar"] = bos_bar if bos_bar else "NONE"
    return result
    
# ================= PRINT DASHBOARD =================
def print_dashboard(data):
    if not data:
        print("No metrics fetched from data pipeline.")
        return

    # 1. CANDLE VISUAL STREAM
    # Terminal-only display substitution; preserve ANSI color codes and shared web data.
    import re
    print(re.sub(r"\x1b\[[0-9;]*m|1", lambda m: "+" if m.group() == "1" else m.group(), data["candle_visual"]))

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
    elif trnd in {"BULL", "UP"}: st_c = Fore.LIGHTGREEN_EX
    elif trnd in {"BEAR", "DOWN"}: st_c = Fore.LIGHTRED_EX
    else: st_c = Fore.YELLOW
    s_st = TOTAL_WIDTH - len(f"Super:{trnd}") - len(f"LINE:{line}")
    print(Fore.WHITE + "Super:" + st_c + trnd + " " * max(1, s_st) + Fore.WHITE + "LINE:" + Fore.CYAN + str(line))

    # 7. RISK METRIC DIRECTION POWER
    ce, pe = data["ce_power"], data["pe_power"]
    ce_c = Fore.LIGHTGREEN_EX if ce > pe else Fore.CYAN
    pe_c = Fore.LIGHTRED_EX if pe > ce else Fore.CYAN
    s_pw = TOTAL_WIDTH - len(f"CE Power:{ce}") - len(f"PE Power:{pe}")
    print(Fore.WHITE + "CE Power:" + ce_c + str(ce) + " " * max(1, s_pw) + Fore.WHITE + "PE Power:" + pe_c + str(pe))

    # 8. INDEPENDENT INDICATOR STATUS
    sma_status = data.get("sma", "NA")
    tsma_status = data.get("tsma", "NA")
    sma_color = Fore.LIGHTGREEN_EX if sma_status == "BULL" else Fore.LIGHTRED_EX if sma_status == "BEAR" else Fore.YELLOW
    tsma_color = Fore.LIGHTGREEN_EX if tsma_status == "BULL" else Fore.LIGHTRED_EX if tsma_status == "BEAR" else Fore.YELLOW
    s_ind = TOTAL_WIDTH - len(f"SMA:{sma_status}") - len(f"TSMA:{tsma_status}")
    print(Fore.WHITE + "SMA:" + sma_color + sma_status + " " * max(1, s_ind) + Fore.WHITE + "TSMA:" + tsma_color + tsma_status)

    # 9. LIVE ORDER SIGNALS (FINAL STATUS ROW)
    ent, ext = data["entry"], data["exit"]
    e_color = Fore.LIGHTGREEN_EX if "BUY" in ent or "UP" in ent else Fore.LIGHTRED_EX if "SELL" in ent or "DOWN" in ent else Fore.YELLOW
    x_color = Fore.LIGHTGREEN_EX if ext in {"BUY", "BULL", "UP"} else Fore.LIGHTRED_EX if ext in {"SELL", "BEAR", "DOWN"} else Fore.YELLOW
    s_e = TOTAL_WIDTH - len(f"Entry:{ent}") - len(f"Exit:{ext}")
    print(Fore.WHITE + "Entry:" + e_color + ent + " " * max(1, s_e) + Fore.WHITE + "Exit:" + x_color + ext)

    # 10. BOS BOUNDARY PRINT MATRIX
    print(data["bos_bar"])

# ================= MAIN RUNNER ENGINE =================
if __name__ == "__main__":
    run_pyc_file()
    snapshot_data = get_full_snapshot(
        monitor=os.environ.get("PXY_MONITOR_MODE") == "1"
    )
    print_dashboard(snapshot_data)

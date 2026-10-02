# =============================================================================
# INFRASTRUCTURE FRAMEWORK LAYER: exeacgpxy.py (acg)
# CORE PROJECT VARIABLES, CONSTRAINTS & MULTI-LAYER RUNTIME SAFETY LOCKS
# =============================================================================
import os
import time
import pytz
from datetime import datetime, time as dt_time
from colorama import Fore, Style, init

init(autoreset=True)

REBUY_ENABLED = True
MAX_LAYERS = 5
COOL_DOWN_SECONDS = 30

PANEL_WIDTH = 42
SCALE_WIDTH = 40

IST = pytz.timezone("Asia/Kolkata")
_COOL_DIR = os.path.dirname(os.path.abspath(__file__))   # cooldown tokens live next to this file, not in the CWD


def _cool_path(side):
    return os.path.join(_COOL_DIR, f"exebal_cool_{side.lower()}.txt")
MARKET_START = dt_time(9, 17)
MARKET_END = dt_time(15, 11)


def safe_float(val, fallback=0.0):
    """Prevents runtime float conversion crashes from NaN, None, or empty strings."""
    if val is None:
        return fallback
    try:
        return float(str(val).replace(',', '').strip())
    except (ValueError, TypeError):
        return fallback


def side_overall_pnl_pct(rows):
    """Blended (overall) P&L% across all layers on one side. Used by System A and B."""
    if rows is None or rows.empty:
        return 0.0
    total_cost = (rows['qty'].apply(safe_float) * rows['buy_prc'].apply(safe_float)).sum()
    total_value = (rows['qty'].apply(safe_float) * rows['sell_prc'].apply(safe_float)).sum()
    return ((total_value - total_cost) / total_cost) * 100 if total_cost > 0 else 0.0


def generate_pxy_tag():
    """Generates localized order tag identification markers."""
    return datetime.now(IST).strftime('%H%M%S')


def set_cooling(side):
    """Creates a local file token lock to execute defensive cooling down tracks."""
    file_path = _cool_path(side)
    try:
        with open(file_path, "w") as f:
            f.write(str(time.time()))
    except Exception as e:
        print(f"{Fore.RED}⚠️ Cooldown Write Error: {e}")


def is_cooling(side):
    """Verifies filesystem locks to prevent duplicate rapid order executions."""
    file_path = _cool_path(side)
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, "r") as f:
            last_ts = float(f.read().strip())
            if (time.time() - last_ts) < COOL_DOWN_SECONDS:
                return True
        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass
        return False
    except Exception:
        return False


def get_loss(row):
    """Calculates instantaneous percentage deviation using execution premiums."""
    entry = safe_float(row.get("buy_prc", 0.0))
    ltp = safe_float(row.get("sell_prc", 0.0))
    return ((ltp - entry) / entry) * 100 if entry > 0 else 0


def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, tag, ce_count, pe_count, trend):
    """Renders a strict 42-character width dashboard upon an order trigger event."""
    border = Fore.YELLOW + "=" * PANEL_WIDTH
    divider = Fore.RED + "-" * PANEL_WIDTH
    header_text = "🚨 PXY® ABSOLUTE GEOMETRY TRIGGERED 🚨"

    print("\n" + border)
    print(Fore.WHITE + header_text.center(PANEL_WIDTH - 2, " "))
    print(divider)
    print(Fore.WHITE + f" • SYMBOL       : {symbol}".ljust(PANEL_WIDTH))
    print(Fore.WHITE + f" • SIDE OPTION   : {side} ({ce_count}CE vs {pe_count}PE)".ljust(PANEL_WIDTH))
    print(Fore.WHITE + f" • ACTIVE TREND  : {trend}".ljust(PANEL_WIDTH))

    loss_txt = f" • CURRENT RETURN: {current_loss:.2f}%"
    print(Fore.WHITE + " • CURRENT RETURN: " + Fore.RED + f"{current_loss:.2f}%" + Style.RESET_ALL + " " * max(0, PANEL_WIDTH - len(loss_txt) - 13))

    target_txt = f" • DYNAMIC TARGET: {int(round(target_threshold))}%"
    print(Fore.WHITE + " • DYNAMIC TARGET: " + Fore.YELLOW + f"{int(round(target_threshold))}%" + Style.RESET_ALL + " " * max(0, PANEL_WIDTH - len(target_txt) - 16))

    print(Fore.WHITE + f" • ORDER TAG     : {tag}".ljust(PANEL_WIDTH))
    print(border + "\n")

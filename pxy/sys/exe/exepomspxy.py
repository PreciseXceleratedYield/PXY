# exepomspxy.py
from colorama import Fore, Style, init
import re

init(autoreset=True)

ansi_escape = re.compile(r'\x1b\[[0-9;]*m')

def visible_len(s):
    return len(ansi_escape.sub('', s))

def color_value(label, val):
    val_str = str(val)
    val_upper = val_str.upper()
    
    if "BUY" in val_upper:
        return Fore.GREEN + val_str + Style.RESET_ALL
    elif "SELL" in val_upper:
        return Fore.RED + val_str + Style.RESET_ALL
    
    elif val_upper in ["UP", "BULL"]:
        return Fore.GREEN + val_str + Style.RESET_ALL
    elif val_upper in ["DOWN", "BEAR"]:
        return Fore.RED + val_str + Style.RESET_ALL
    
    elif label in ["CE Power 🟢", "PE Power 🔴"] and float(val) > 1:
        return Fore.YELLOW + val_str + Style.RESET_ALL
    elif label in ["CE Depth 🟢", "PE Depth 🔴"] and float(val) > 1:
        return Fore.MAGENTA + val_str + Style.RESET_ALL
    
    elif isinstance(val, (int, float)):
        return Fore.CYAN + val_str + Style.RESET_ALL
    else:
        return val_str

def print_market_dashboard(market_df):
    if market_df.empty:
        print("No market snapshot available")
        return

    snapshot = market_df.iloc[0].to_dict()

    # Regular metrics
    metrics = [
        ("📏  ATR", "atr"),
        ("🧭  Mullu", "direction"),
        ("🚀  Super", "supertrend"),
        ("📊  LINE", "super_line"),
        ("🟢  CE Power", "ce_power"),
        ("🔴  PE Power", "pe_power"),
        ("🎯  Entry", "entry"),
        ("🎯  Exits", "exit"),  # renamed here
    ]
    
    # Depth metrics last
    depth_metrics = [
        ("🟢  CE Depth", "hkin_ce_depth"),
        ("🔴  PE Depth", "hkin_pe_depth"),
    ]

    row_width = 40
    values = []
    for label, col in metrics:
        val = snapshot.get(col, "NA")
        val_colored = color_value(label, val)
        values.append(f"{label}:{val_colored}")

    for i in range(0, len(values), 2):
        left = values[i]
        right = values[i+1] if i+1 < len(values) else ""
        spaces = row_width - visible_len(left) - visible_len(right)
        spaces = spaces if spaces > 0 else 2
        print(f"{left}{' ' * spaces}{right}")

    # Depth metrics
    depth_values = []
    for label, col in depth_metrics:
        val = snapshot.get(col, "NA")
        val_colored = color_value(label, val)
        depth_values.append(f"{label}:{val_colored}")

    if depth_values:
        left = depth_values[0]
        right = depth_values[1] if len(depth_values) > 1 else ""
        spaces = row_width - visible_len(left) - visible_len(right)
        spaces = spaces if spaces > 0 else 2
        print(f"{left}{' ' * spaces}{right}")

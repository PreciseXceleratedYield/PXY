# exepomspxy.py
from colorama import Fore, Style, init
import re
import subprocess
import sys

init(autoreset=True)
ansi_escape = re.compile(r'\x1b\[[0-9;]*m')

def visible_len(s):
    return len(ansi_escape.sub('', s))

# ---------------- VALUE ONLY COLOR SCAN ----------------
def color_value(val):
    val_str = str(val)
    val_upper = val_str.upper()
    dark_green = Style.DIM + Fore.GREEN
    dark_red = Style.DIM + Fore.RED
    
    if "BUY" in val_upper:
        return dark_green + val_str + Style.RESET_ALL
    elif "SELL" in val_upper:
        return dark_red + val_str + Style.RESET_ALL
    elif "UP" in val_upper or "BULL" in val_upper:
        return dark_green + val_str + Style.RESET_ALL
    elif "DOWN" in val_upper or "BEAR" in val_upper:
        return dark_red + val_str + Style.RESET_ALL
    return Style.DIM + Fore.CYAN + val_str + Style.RESET_ALL

def print_market_dashboard(market_df):
    if market_df.empty:
        print("No market snapshot available")
        return
        
    snapshot = market_df.iloc[0].to_dict()

    # ===== DAY CONTEXT =====
    subprocess.run([sys.executable, "systdaypxy.py"])

    metrics = [
        ("📏  ATR", "atr"), ("🧭 Mullu", "direction"),
        ("🚀  Super", "supertrend"), ("📊 LINE", "super_line"),
        ("🟢  CE Power", "ce_power"), ("🔴 PE Power", "pe_power"),
        ("🟩  CE Force", "ce_force"), ("🟥 PE Force", "pe_force"),
        ("🟢  CE Depth", "hkin_ce_depth"), ("🔴 PE Depth", "hkin_pe_depth"),
        ("🎯  Entry", "entry"), ("🎯 Exit", "exit"),
    ]

    depth_metrics = []
    row_width = 41
    values = []

    # ---------------- BUILD METRICS (With Surgical Decimal Fix) ----------------
    for label, col in metrics:
        val = snapshot.get(col, "NA")
        
        # FIX: Truncate Power and Force to 2 decimals
        if "Power" in label or "Force" in label:
            try:
                val = f"{float(val):.2f}"
            except (ValueError, TypeError):
                pass
                
        val_colored = color_value(val)
        values.append((label, col, val_colored))

    # ---------------- PRINT MAIN DASHBOARD ----------------
    for i in range(0, len(values), 2):
        # LEFT SIDE
        l_label, l_col, l_val = values[i]
        left = f"{l_label}: {l_val}"

        # RIGHT SIDE
        if i + 1 < len(values):
            r_label, r_col, _ = values[i + 1]
            raw_val = snapshot.get(r_col, "NA")
            
            # FIX: Truncate Right Side Power and Force
            if "Power" in r_label or "Force" in r_label:
                try:
                    raw_val = f"{float(raw_val):.2f}"
                except:
                    pass
            
            raw_val_colored = color_value(raw_val)
            parts = r_label.split()
            emoji = parts[0] if len(parts) >= 2 else ""
            label_text = " ".join(parts[1:]) if len(parts) >= 2 else r_label
            right = f"{raw_val_colored}: {label_text} {emoji}"
        else:
            right = ""

        spaces = row_width - visible_len(left) - visible_len(right)
        spaces = spaces if spaces > 0 else 2
        print(f"{left}{' ' * spaces}{right}")

    # ---------------- DEPTH SECTION ----------------
    depth_values = []
    for label, col in depth_metrics:
        val = snapshot.get(col, "NA")
        val_colored = color_value(val)
        depth_values.append((label, col, val_colored))

    if depth_values:
        l_label, l_col, l_val = depth_values[0]
        left = f"{l_label}: {l_val}"
        if len(depth_values) > 1:
            r_label, r_col, _ = depth_values[1]
            raw_val = snapshot.get(r_col, "NA")
            raw_val_colored = color_value(raw_val)
            parts = r_label.split()
            emoji = parts[0] if len(parts) >= 2 else ""
            label_text = " ".join(parts[1:]) if len(parts) >= 2 else r_label
            right = f"{raw_val_colored}: {label_text} {emoji}"
        else:
            right = ""
        spaces = row_width - visible_len(left) - visible_len(right)
        spaces = spaces if spaces > 0 else 2
        print(f"{left}{' ' * spaces}{right}")

    # ===== BOS & VISUAL =====
    print(snapshot.get("bos_bar", "NONE"))
    print(snapshot.get("candle_visual", ""))


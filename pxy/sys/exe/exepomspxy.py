# exepomspxy.py
from colorama import Fore, Style, init
import re

init(autoreset=True)

ansi_escape = re.compile(r'\x1b\[[0-9;]*m')


def visible_len(s):
    return len(ansi_escape.sub('', s))


# ---------------- VALUE ONLY COLOR SCAN ----------------
def color_value(val):
    val_str = str(val)
    val_upper = val_str.upper()

    if "BUY" in val_upper:
        return Fore.GREEN + val_str + Style.RESET_ALL
    elif "SELL" in val_upper:
        return Fore.RED + val_str + Style.RESET_ALL
    elif "UP" in val_upper or "BULL" in val_upper:
        return Fore.GREEN + val_str + Style.RESET_ALL
    elif "DOWN" in val_upper or "BEAR" in val_upper:
        return Fore.RED + val_str + Style.RESET_ALL

    return Fore.CYAN + val_str + Style.RESET_ALL


def print_market_dashboard(market_df):
    if market_df.empty:
        print("No market snapshot available")
        return

    snapshot = market_df.iloc[0].to_dict()

    
    # ===== DAY CONTEXT =====
    import subprocess
    import sys
    
    subprocess.run([sys.executable, "systdaypxy.py"])
    
    metrics = [
        ("📏  ATR", "atr"),
        ("🧭 Mullu", "direction"),
        ("🚀  Super", "supertrend"),
        ("📊 LINE", "super_line"),
        ("🟢  CE Power", "ce_power"),
        ("🔴 PE Power", "pe_power"),
        ("🟩  CE Force", "ce_force"),
        ("🟥 PE Force", "pe_force"),        
        ("🟢  CE Depth", "hkin_ce_depth"),
        ("🔴 PE Depth", "hkin_pe_depth"),   
        ("🎯  Entry", "entry"),
        ("🎯 Exit", "exit"),
    ]

    depth_metrics = [

    ]

    row_width = 41
    values = []

    # ---------------- BUILD METRICS ----------------
    for label, col in metrics:
        val = snapshot.get(col, "NA")
        val_colored = color_value(val)
        values.append((label, col, val_colored))

    # ---------------- PRINT MAIN DASHBOARD ----------------
    for i in range(0, len(values), 2):

        # LEFT SIDE
        l_label, l_col, l_val = values[i]
        left = f"{l_label}: {l_val}"

        # RIGHT SIDE (FIXED: VALUE ALSO COLORED)
        if i + 1 < len(values):
            r_label, r_col, _ = values[i + 1]

            raw_val = snapshot.get(r_col, "NA")
            raw_val_colored = color_value(raw_val)

            parts = r_label.split()
            if len(parts) >= 2:
                emoji = parts[0]
                label_text = " ".join(parts[1:])
            else:
                emoji = ""
                label_text = r_label

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
            if len(parts) >= 2:
                emoji = parts[0]
                label_text = " ".join(parts[1:])
            else:
                emoji = ""
                label_text = r_label

            right = f"{raw_val_colored}: {label_text} {emoji}"
        else:
            right = ""

        spaces = row_width - visible_len(left) - visible_len(right)
        spaces = spaces if spaces > 0 else 2

        print(f"{left}{' ' * spaces}{right}")
    # ===== BOS =====
    print(snapshot.get("bos_bar", "NONE"))
    # ===== VISUAL =====
    print(snapshot.get("candle_visual", ""))

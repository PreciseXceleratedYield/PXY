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
    
    # High Contrast for signals only
    br_green = Fore.LIGHTGREEN_EX + Style.BRIGHT
    br_red = Fore.LIGHTRED_EX + Style.BRIGHT
    br_yellow = Fore.LIGHTYELLOW_EX + Style.BRIGHT

    if "BUY" in val_upper:
        return br_green + val_str + Style.RESET_ALL
    elif "SELL" in val_upper:
        return br_red + val_str + Style.RESET_ALL
    elif "UP" in val_upper or "BULL" in val_upper:
        return Fore.LIGHTGREEN_EX + val_str + Style.RESET_ALL
    elif "DOWN" in val_upper or "BEAR" in val_upper:
        return Fore.LIGHTRED_EX + val_str + Style.RESET_ALL
    elif "SIDE" in val_upper or "NONE" in val_upper:
        return br_yellow + val_str + Style.RESET_ALL
        
    # Numbers and non-signals get clean, non-bright Cyan
    return Fore.CYAN + val_str + Style.RESET_ALL

def print_market_dashboard(market_df):
    if market_df.empty:
        print(Fore.RED + "No market snapshot available")
        return

    snapshot = market_df.iloc[0].to_dict()

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

    row_width = 41
    values = []

    # ---------------- BUILD METRICS ----------------
    for label, col in metrics:
        val = snapshot.get(col, "NA")
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
        left = f"{Fore.WHITE}{l_label}: {l_val}"

        # RIGHT SIDE
        if i + 1 < len(values):
            r_label, r_col, _ = values[i + 1]
            raw_val = snapshot.get(r_col, "NA")
            
            if "Power" in r_label or "Force" in r_label:
                try:
                    raw_val = f"{float(raw_val):.2f}"
                except:
                    pass
                    
            raw_val_colored = color_value(raw_val)
            parts = r_label.split()
            emoji = parts[0] if len(parts) >= 2 else ""
            label_text = " ".join(parts[1:]) if len(parts) >= 2 else r_label
            
            right = f"{raw_val_colored}: {Fore.WHITE}{label_text} {emoji}"
        else:
            right = ""

        spaces = row_width - visible_len(left) - visible_len(right)
        spaces = max(2, spaces)
        print(f"{left}{' ' * spaces}{right}")

    # ===== BOS & VISUAL =====
    print(snapshot.get("bos_bar", "NONE"))
    print(snapshot.get("candle_visual", ""))


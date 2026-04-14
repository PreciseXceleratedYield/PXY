from colorama import Fore, Style, init
import re

init(autoreset=True)

ansi_escape = re.compile(r'\x1b\[[0-9;]*m')


def visible_len(s):
    return len(ansi_escape.sub('', s))


# ---------------- VALUE COLOR ONLY ----------------
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
        print("No data")
        return

    snapshot = market_df.iloc[0].to_dict()

    metrics = [
        ("ATR", "atr"),
        ("Mullu", "direction"),
        ("Super", "supertrend"),
        ("LINE", "super_line"),
        ("CE Power", "ce_power"),
        ("PE Power", "pe_power"),
        ("Entry", "entry"),
        ("Exit", "exit"),
    ]

    row_width = 40
    values = []

    # ---------------- BUILD DATA ----------------
    for label, col in metrics:
        val_raw = snapshot.get(col, "NA")
        val_colored = color_value(val_raw)

        values.append((label, col, val_raw, val_colored))

    # ---------------- PRINT ----------------
    for i in range(0, len(values), 2):

        # LEFT SIDE (VALUE → LABEL, COLORED VALUE)
        l_label, l_col, l_raw, l_colored = values[i]
        left = f"{l_colored}: {l_label}"

        # RIGHT SIDE (VALUE → LABEL, COLORED VALUE)
        if i + 1 < len(values):
            r_label, r_col, r_raw, r_colored = values[i + 1]
            right = f"{r_colored}: {r_label}"
        else:
            right = ""

        spaces = row_width - visible_len(left) - visible_len(right)
        spaces = spaces if spaces > 0 else 2

        print(f"{left}{' ' * spaces}{right}")

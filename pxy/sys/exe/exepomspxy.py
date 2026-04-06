# exepomspxy.py
from colorama import Fore, Style, init

init(autoreset=True)

def color_value(label, val):
    """
    Apply context-based coloring for values only.
    Labels and emojis remain plain.
    """
    # Direction / Mullu / Supertrend / Entry / Signal
    if str(val).upper() in ["UP", "BULL", "BUY"]:
        return Fore.GREEN + str(val) + Style.RESET_ALL
    elif str(val).upper() in ["DOWN", "BEAR", "SELL"]:
        return Fore.RED + str(val) + Style.RESET_ALL
    # Power metrics
    elif label in ["CE Power 🟢⚡", "PE Power 🔴⚡"] and float(val) > 0:
        return Fore.YELLOW + str(val) + Style.RESET_ALL
    # Numeric (ATR, LINE)
    elif isinstance(val, (int, float)):
        return Fore.CYAN + str(val) + Style.RESET_ALL
    else:
        return str(val)

def print_market_dashboard(market_df):
    """
    Prints a 42-char emoji dashboard from a single-row market_df.
    Only values are colored.
    """
    if market_df.empty:
        print("No market snapshot available")
        return

    snapshot = market_df.iloc[0].to_dict()

    metrics = [
        ("ATR 📏", "atr"),
        ("Mullu 🧭", "direction"),
        ("Super 🚀", "supertrend"),
        ("LINE 📊", "super_line"),
        ("CE Power 🟢", "ce_power"),
        ("PE Power 🔴", "pe_power"),
        ("Entry 🎯", "entry"),
        ("Signal 📡", "exit"),
    ]

    row_width = 42
    values = []
    for label, col in metrics:
        val = snapshot.get(col, "NA")
        val_colored = color_value(label, val)
        values.append(f"{label}:{val_colored}")

    # Print two metrics per row
    for i in range(0, len(values), 2):
        left = values[i]
        right = values[i+1] if i+1 < len(values) else ""
        spaces = row_width - len(left) - len(right)
        spaces = spaces if spaces > 0 else 2
        print(f"{left}{' ' * spaces}{right}")

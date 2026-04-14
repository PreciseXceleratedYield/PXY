from colorama import Fore, Style, init

init(autoreset=True)


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

    # ---------------- SPLIT INTO LEFT / RIGHT ----------------
    mid = len(metrics) // 2
    left_metrics = metrics[:mid]
    right_metrics = metrics[mid:]

    # ---------------- LEFT SIDE ----------------
    for label, col in left_metrics:
        val = snapshot.get(col, "NA")
        val_colored = color_value(val)
        print(f"{label}: {val_colored}")

    print()  # separator

    # ---------------- RIGHT SIDE ----------------
    for label, col in right_metrics:
        val = snapshot.get(col, "NA")
        val_colored = color_value(val)
        print(f"{val_colored}: {label}")

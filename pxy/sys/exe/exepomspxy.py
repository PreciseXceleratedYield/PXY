# exepomspxy.py

def print_market_dashboard(market_df):
    """
    Prints a 42-char emoji dashboard from a single-row market_df.
    Assumes market_df has columns: atr, direction, supertrend, super_line, ce_power,
    pe_power, entry, exit
    """
    if market_df.empty:
        print("No market snapshot available")
        return

    # Take the first row as snapshot
    snapshot = market_df.iloc[0].to_dict()

    # --- Metrics mapping ---
    metrics = [
        ("ATR 📏", "atr"),
        ("Mullu 🧭", "direction"),
        ("Super 🚀", "supertrend"),
        ("LINE 📊", "super_line"),
        ("CE Power 🟢⚡", "ce_power"),
        ("PE Power 🔴⚡", "pe_power"),
        ("Entry 🎯", "entry"),
        ("Signal 📡", "exit"),
    ]

    row_width = 42
    values = []
    for label, col in metrics:
        val = snapshot.get(col, "NA")
        values.append(f"{label}:{val}")

    # Print two metrics per row
    for i in range(0, len(values), 2):
        left = values[i]
        right = values[i+1] if i+1 < len(values) else ""
        spaces = row_width - len(left) - len(right)
        spaces = spaces if spaces > 0 else 2
        print(f"{left}{' ' * spaces}{right}")

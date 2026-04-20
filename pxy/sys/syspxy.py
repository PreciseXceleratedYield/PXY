from sysdashpxy import get_full_snapshot
from syscnfgpxy import TICKER
from syschrtpxy import export_supertrend_json


def get_all_data():
    # -------- RUN CHART GENERATION FIRST --------
    export_supertrend_json()

    # -------- CORE --------
    core = get_full_snapshot() or {}

    data = {
        # ===== CORE =====
        "hkin_signal": core.get("hkin_signal", "NONE"),
        "hkin_past_depth": core.get("hkin_past_depth", 0),
        "hkin_ce_depth": core.get("hkin_ce_depth", 1),
        "hkin_pe_depth": core.get("hkin_pe_depth", 1),
        "atr": core.get("atr"),
        "katr": core.get("katr"),
        "price": core.get("price"),
        "direction": core.get("direction"),
        "supertrend": core.get("supertrend"),
        "super_line": core.get("super_line"),
        "ce_power": core.get("ce_power"),
        "pe_power": core.get("pe_power"),
        "entry": core.get("entry"),
        "exit": core.get("exit"),
    }

    return data


# ===== SELF TEST =====
if __name__ == "__main__":
    data = get_all_data()
    for k, v in data.items():
        print(f"{k:18}: {v}")


# syspxy.py
import json
import os
from datetime import datetime

from sysdashpxy import get_full_snapshot
from sysstrndpxy import export_supertrend_json


def get_all_data():

    # -------- CORE --------
    core = get_full_snapshot() or {}

    # -------- RUN TREND CHART GENERATION FROM THE SAME SNAPSHOT --------
    export_supertrend_json(
        core.get("chart_df", core.get("df"))
    )

    # -------- PRICE LOGIC (DTAF BLENDED PRICE) --------
    # DTAF already blends NIFTY FUT into INDEX OHLC.
    # Use the resulting core price directly.
    final_price = core.get("price")

    # -------- COMBINE --------
    data = {
        # ===== SYSTEM TIMING =====
        "timestamp": datetime.now().isoformat(),

        # ===== CORE =====
        "hkin_signal": core.get("hkin_signal", "NONE"),
        "hkin_past_depth": core.get("hkin_past_depth", 0),
        "hkin_ce_depth": core.get("hkin_ce_depth", 1),
        "hkin_pe_depth": core.get("hkin_pe_depth", 1),
        "hkin_signal_time": core.get("hkin_signal_time"),

        "atr": core.get("atr"),
        "katr": core.get("katr"),
        "price": final_price,
        "direction": core.get("direction"),

        "supertrend": core.get("supertrend"),
        "super_line": core.get("super_line"),
        "sma": core.get("sma", "NA"),

        "ce_power": core.get("ce_power"),
        "pe_power": core.get("pe_power"),

        # FORCE FIX (SINGLE ADDITION)
        "ce_force": core.get("ce_force", 1.0),
        "pe_force": core.get("pe_force", 1.0),

        "entry": core.get("entry"),
        "exit": core.get("exit"),
        "market_data_available": core.get(
            "market_data_available", False
        ),

        # ===== NEW =====
        "candle_visual": core.get("candle_visual", ""),
        "bos_bar": core.get("bos_bar", "NONE"),
        "bos_val": core.get("bos_val", "0%"),
        "day_candle": core.get("day_candle", ""),
    }

    # -------- TARGET: pxy/web DIRECTORY --------
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.abspath(
        os.path.join(current_dir, "..", "web")
    )

    # Safeguard: Create web folder if it's missing
    os.makedirs(target_dir, exist_ok=True)

    target_file = os.path.join(
        target_dir,
        "webdashpxy.json"
    )

    # Overwrite deployment
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    return data


# ===== SELF TEST =====
if __name__ == "__main__":
    data = get_all_data()

    for k, v in data.items():
        print(f"{k:18}: {v}")


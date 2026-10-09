# syspxy.py
import json
import math
import os
import subprocess
from pathlib import Path
from datetime import datetime
from sysdashpxy import get_full_snapshot
from sysmodepxy import dispatch_mode

# Import the clean json exporter from your streamlined trend engine
from sysstrndpxy import export_supertrend_json


def _get_production_nftfut_price():
    fut_file_path = Path(__file__).resolve().parent / "exe" / "run" / "nftfut.json"
    if not fut_file_path.exists():
        print(f"Warning: {fut_file_path} not found. Using fallback price calculation.")
        return None
    try:
        with fut_file_path.open("r", encoding="utf-8") as f:
            fut_data = json.load(f)
        if isinstance(fut_data, list):
            target = fut_data[-1] if fut_data else {}
        elif isinstance(fut_data, dict):
            target = fut_data
        else:
            target = {}
        if not isinstance(target, dict):
            target = {}
        price = float(
            target.get("price", target.get("Close", target.get("last_price", 0)))
        )
        if not math.isfinite(price) or price <= 0:
            print(f"Warning: {fut_file_path} contains no valid positive futures price.")
            return None
        return price
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"Warning: Failed to read or parse {fut_file_path}: {error}")
        return None


def get_all_data():
    # -------- RUN THE SCRIPT GLOBALLY FIRST --------
    def run_production_futures_sidecar():
        sidecar_path = Path(__file__).resolve().parent.parent / "pxyfut"
        if not sidecar_path.is_file():
            print(f"Warning: Futures sidecar {sidecar_path} not found.")
            return
        try:
            subprocess.run(["bash", str(sidecar_path)], check=True)
        except (subprocess.CalledProcessError, OSError) as error:
            print(f"Warning: Could not execute futures sidecar {sidecar_path}: {error}")

    dispatch_mode("run_futures_sidecar", run_production_futures_sidecar)

    # -------- CORE --------
    core = get_full_snapshot() or {}

    # -------- RUN TREND CHART GENERATION FROM THE SAME SNAPSHOT --------
    export_supertrend_json(core.get("chart_df", core.get("df")))

    # -------- DYNAMIC PRICE LOGIC (FUT AVERAGE OR FALLBACK) --------
    try:
        base_price = float(core.get("price", 0) or 0)
    except (TypeError, ValueError):
        base_price = 0.0
    if not math.isfinite(base_price):
        base_price = 0.0
    final_price = base_price + 50
    
    fut_price = dispatch_mode("get_nftfut_price", _get_production_nftfut_price)
    if fut_price is not None:
        try:
            base_price = float(base_price)
            fut_price = float(fut_price)
            if math.isfinite(base_price) and math.isfinite(fut_price):
                if abs(base_price - fut_price) <= 200:
                    final_price = (base_price + fut_price) / 2
                else:
                    print(
                        f"Warning: FUT price ({fut_price}) outside ±200 range "
                        f"of base ({base_price}). Using fallback."
                    )
        except (TypeError, ValueError):
            print("Warning: Invalid base or futures price. Using fallback.")

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
        "price": final_price,  # DYNAMICALLY COMPUTED PRICE
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
        "market_data_available": core.get("market_data_available", False),

        # ===== NEW =====
        "candle_visual": core.get("candle_visual", ""),
        "bos_bar": core.get("bos_bar", "NONE"),
        "bos_val": core.get("bos_val", "0%"),
        "day_candle": core.get("day_candle", ""),
    }

    # -------- 📁 TARGET: pxy/web DIRECTORY --------
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.abspath(os.path.join(current_dir, "..", "web"))
    
    # Safeguard: Create web folder if it's missing
    os.makedirs(target_dir, exist_ok=True) 
    
    target_file = os.path.join(target_dir, "webdashpxy.json")
    
    # Overwrite deployment
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    return data


# ===== SELF TEST =====
if __name__ == "__main__":
    data = get_all_data()
    for k, v in data.items():
        print(f"{k:18}: {v}")

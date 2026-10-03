# syspxy.py
import json
import os
import subprocess
from datetime import datetime
from sysdashpxy import get_full_snapshot
from systdaypxy import get_market_snapshot  # Keep your original 'systdaypxy'
from sysvixpxy import get_market_context, expand_vix, expand_sentiment
from syscnfgpxy import TICKER
from sysmodepxy import dispatch_mode

# Import the clean json exporter from your streamlined trend engine
from sysstrndpxy import export_supertrend_json

def get_all_data():
    # -------- RUN THE SCRIPT GLOBALLY FIRST --------
    def run_production_futures_sidecar():
        try:
            subprocess.run(["pxyfut"], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Warning: Could not execute 'pxyfut' command: {e}")

    dispatch_mode("run_futures_sidecar", run_production_futures_sidecar)

    # -------- RUN TREND CHART GENERATION SECOND --------
    export_supertrend_json()

    # -------- CORE --------
    core = get_full_snapshot() or {}

    # -------- DASH --------
    dash = get_market_snapshot(TICKER) or {}

    # -------- VIX --------
    vix_flag, sentiment_flag = get_market_context() or (None, None)
    vix_text = expand_vix(vix_flag) if vix_flag else None
    sentiment_text = expand_sentiment(sentiment_flag) if sentiment_flag else None

    # -------- DYNAMIC PRICE LOGIC (FUT AVERAGE OR FALLBACK) --------
    base_price = core.get("price", 0)
    final_price = base_price + 50  # Keep your original blind +50 as the default fallback
    
    fut_file_path = os.path.expanduser("~/pxy/sys/exe/run/nftfut.json")
    if os.path.exists(fut_file_path):
        try:
            with open(fut_file_path, "r", encoding="utf-8") as f:
                fut_data = json.load(f)
                fut_price = None
                
                # Check if JSON is a list of rolling records and pull the last item
                if isinstance(fut_data, list) and len(fut_data) > 0:
                    latest_record = fut_data[-1]
                    if isinstance(latest_record, dict):
                        fut_price = latest_record.get("price")
                # Fallback to check if it's still a flat dictionary
                elif isinstance(fut_data, dict):
                    fut_price = fut_data.get("price")
                
                if fut_price is not None:
                    # Check if the FUT price is within ±200 of our base price
                    if abs(base_price - fut_price) <= 200:
                        final_price = (base_price + fut_price) / 2
                    else:
                        print(f"Warning: FUT price ({fut_price}) outside ±200 range of base ({base_price}). Using fallback.")
        except Exception as e:
            print(f"Warning: Failed to read or parse nftfut.json: {e}")
    else:
        print(f"Warning: {fut_file_path} not found. Using fallback price calculation.")

    # -------- COMBINE --------
    data = {
        # ===== SYSTEM TIMING =====
        "timestamp": datetime.now().isoformat(),

        # ===== DASH =====
        "bias": dash.get("bias"),
        "o_change": dash.get("o_change"),
        "m_change": dash.get("m_change"),

        # RENAMED FIELDS
        "TO": dash.get("open"),
        "high": dash.get("high"),
        "low": dash.get("low"),
        "YC": dash.get("prev_close"),

        # ===== CORE =====
        "hkin_signal": core.get("hkin_signal", "NONE"),
        "hkin_past_depth": core.get("hkin_past_depth", 0),
        "hkin_ce_depth": core.get("hkin_ce_depth", 1),
        "hkin_pe_depth": core.get("hkin_pe_depth", 1),

        "atr": core.get("atr"),
        "katr": core.get("katr"),
        "price": final_price,  # DYNAMICALLY COMPUTED PRICE
        "direction": core.get("direction"),

        "supertrend": core.get("supertrend"),
        "super_line": core.get("super_line"),

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

        # ===== VIX =====
        "vix_flag": vix_flag,
        "vix_mode": vix_text,
        "global_flag": sentiment_flag,
        "global_sentiment": sentiment_text
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

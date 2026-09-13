# syspxy.py
import json
import os
import subprocess
from datetime import datetime
from sysdashpxy import get_full_snapshot
from systdaypxy import get_market_snapshot  # Keep your original 'systdaypxy'
from sysvixpxy import get_market_context, expand_vix, expand_sentiment
from syscnfgpxy import TICKER

# Import the clean json exporter from your streamlined trend engine
from sysstrndpxy import export_supertrend_json

def get_all_data():
    # -------- RUN THE SCRIPT GLOBALLY FIRST --------
    try:
        # Runs 'pxyfut' as a general terminal command from anywhere
        subprocess.run(["pxyfut"], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Warning: Could not execute 'pxyfut' command: {e}")

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
        "price": core.get("price") + 50,
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


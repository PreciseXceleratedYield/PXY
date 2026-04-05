# syspxy.py

from sysdashpxy import get_full_snapshot
from systdaypxy import get_market_snapshot
from sysvixpxy import get_market_context, expand_vix, expand_sentiment
from syscnfgpxy import TICKER

import csv
import os

# ================= GLOBAL =================
CSV_FILE = "line_data.csv"
last_candle_time = None


# ================= CSV APPENDER =================
def append_csv(data):
    global last_candle_time

    ts = data.get("timestamp")
    close = data.get("close_price")

    if not ts or close is None:
        return

    # ✅ only new candle
    if ts == last_candle_time:
        return

    last_candle_time = ts

    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["time", "close"])

        writer.writerow([ts, close])


# ================= MAIN FUNCTION =================
def get_all_data():
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
        # ===== DASH =====
        "bias": dash.get("bias"),
        "power": dash.get("power"),
        "breakout": dash.get("breakout"),
        "o_change": dash.get("o_change"),
        "m_change": dash.get("m_change"),
        "open": dash.get("open"),
        "high": dash.get("high"),
        "low": dash.get("low"),
        "close": dash.get("close"),

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
        "reversal": core.get("reversal"),

        # ===== CHART DATA =====
        "timestamp": core.get("timestamp"),
        "close_price": core.get("close"),

        # ===== VIX =====
        "vix_flag": vix_flag,
        "vix_mode": vix_text,
        "global_flag": sentiment_flag,
        "global_sentiment": sentiment_text
    }

    # 🔥 AUTO WRITE CSV HERE
    append_csv(data)

    return data


# ===== OPTIONAL DEBUG =====
if __name__ == "__main__":
    data = get_all_data()
    for k, v in data.items():
        print(f"{k:18}: {v}")

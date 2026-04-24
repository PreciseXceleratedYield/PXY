from sysdashpxy import get_full_snapshot
from systdaypxy import get_market_snapshot
from sysvixpxy import get_market_context, expand_vix, expand_sentiment
from syscnfgpxy import TICKER

# 🔥 ADD THIS
from syschrtpxy import export_supertrend_json


def get_all_data():
    # -------- RUN CHART GENERATION FIRST --------
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
        # ===== DASH =====
        "bias": dash.get("bias"),
        "o_change": dash.get("o_change"),
        "m_change": dash.get("m_change"),

        # 🔥 RENAMED FIELDS
        "TO": dash.get("open"),
        "high": dash.get("high"),
        "low": dash.get("low"),
        "YK": dash.get("prev_close"),

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

        # ===== NEW =====
        "candle_visual": core.get("candle_visual", ""),
        "bos_bar": core.get("bos_bar", "NONE"),
        "day_candle": core.get("day_candle", ""),

        # ===== VIX =====
        "vix_flag": vix_flag,
        "vix_mode": vix_text,
        "global_flag": sentiment_flag,
        "global_sentiment": sentiment_text
    }

    return data


# ===== SELF TEST =====
if __name__ == "__main__":
    data = get_all_data()
    for k, v in data.items():
        print(f"{k:18}: {v}")

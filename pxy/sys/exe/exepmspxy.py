import sys
import os
import traceback
from pathlib import Path
import pandas as pd
import pytz
from datetime import datetime
from colorama import Fore, Style

# Frontline mid-price engine import
from runltpspxy import get_mid_price

def safe_float_convert(val, default=None):
    """Pre-scrubs raw system objects and converts to float values safely."""
    if val is None or pd.isna(val):
        return default
    try:
        clean_val = str(val).replace(',', '').strip()
        return float(clean_val)
    except Exception:
        return default

def safe_int_convert(val, default=0):
    """Converts strings and float variations into true integers safely."""
    if val is None or pd.isna(val):
        return default
    try:
        clean_val = str(val).split('.')[0].replace(',', '').strip()
        return int(clean_val)
    except Exception:
        return default

def get_sell_suffix():
    """Generates an explicit millisecond sell tracking suffix."""
    IST = pytz.timezone("Asia/Kolkata")
    ms = datetime.now(IST).strftime('%f')[:-3]
    return f"_S{ms}"

def fetch_live_mid_price(client, row, token_col, seg_col):
    """5-Tiered Pricing Matrix: Traverses your production lookup priority sequence."""
    live_val = 0.0
    raw_token = row.get(token_col) if token_col else None
    token_id = str(raw_token).split('.')[0].strip() if raw_token else None
    raw_seg = str(row.get(seg_col, "nse_fo")).strip()
    ex_seg = "nse_fo" if raw_seg.lower() in ["nse_fo", "nfo"] else raw_seg.lower()

    if not client or not token_id:
        return live_val

    # Tier 1: Primary Mid-Price Call
    try:
        live_val = float(get_mid_price(client, token_id, ex_seg))
    except Exception:
        pass

    # Tier 2 & 3: Structured client.quotes Array/Dict Fallbacks
    if live_val <= 0:
        try:
            t_payload = [{"instrument_token": str(token_id), "exchange_segment": str(ex_seg)}]
            v2_q = client.quotes(instrument_tokens=t_payload, quote_type="ltp")
            if isinstance(v2_q, dict):
                data_chunk = v2_q.get("data") or v2_q.get("message") or v2_q
                if isinstance(data_chunk, list) and len(data_chunk) > 0:
                    live_val = float(data_chunk[0].get("ltp") or data_chunk[0].get("lastTradedPrice") or 0)
                elif isinstance(data_chunk, dict):
                    live_val = float(data_chunk.get("ltp") or data_chunk.get("lastTradedPrice") or 0)
            elif isinstance(v2_q, list) and len(v2_q) > 0:
                live_val = float(v2_q[0].get("ltp") or v2_q[0].get("lastTradedPrice") or 0)
        except Exception:
            pass

    # Tier 4 & 5: client.search_scrip List/Dict Fallbacks
    if live_val <= 0:
        try:
            scr_res = client.search_scrip(exchangeSegment=ex_seg, instrumentToken=str(token_id))
            if isinstance(scr_res, list) and len(scr_res) > 0:
                live_val = float(scr_res[0].get("ltp") or scr_res[0].get("lastPrice") or 0)
            elif isinstance(scr_res, dict):
                live_val = float(scr_res.get("ltp") or scr_res.get("lastPrice") or 0)
        except Exception:
            pass

    return live_val

def get_positions_df(client):
    """Fetches real-time open positions directly from the broker API."""
    try:
        res = client.positions()
        if res and "data" in res and res["data"]:
            return pd.DataFrame(res["data"])
        return pd.DataFrame()
    except Exception:
        print(f"{Fore.RED}[DEBUG CRITICAL] Broker API Positions Call Crashed. Full Traceback:")
        traceback.print_exc()
        return pd.DataFrame()

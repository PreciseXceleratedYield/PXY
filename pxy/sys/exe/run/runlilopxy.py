# run/runlilopxy.py 
import pandas as pd
import json
import os
from datetime import datetime
from runclntpxy import get_session
from runltpspxy import get_mid_price

# =========================
# ⚙️ CONFIGURATION
# =========================
MATCH_MODE = "PFO" 
MEMORY_FILE = os.path.expanduser("~/pxy/pnl.json")

def rotate_daily_file():
    try:
        if not os.path.exists(MEMORY_FILE): return
        now = datetime.now()
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        mtime = datetime.fromtimestamp(os.path.getmtime(MEMORY_FILE))
        if now >= market_open and mtime < market_open:
            date_str = mtime.strftime("%Y-%m-%d")
            archive_path = MEMORY_FILE.replace(".json", f"_{date_str}.json")
            os.rename(MEMORY_FILE, archive_path)
    except: pass

def dump_to_json(banked_pnl, processed_ids):
    try:
        data = {"banked_pnl": int(banked_pnl), "processed_ids": list(processed_ids)}
        with open(MEMORY_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except: pass

def process_lilo_orders(client):
    try:
        rotate_daily_file()
        banked_pnl, processed_ids = 0, set()
        
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r") as f:
                hist = json.load(f)
                banked_pnl = hist.get("banked_pnl", 0)
                processed_ids = set(hist.get("processed_ids", []))

        res = client.order_report()
        if not res or "data" not in res: return pd.DataFrame(), pd.DataFrame()

        df = pd.DataFrame(res["data"])
        df = df[df["ordSt"].isin(["complete", "traded"])].copy()
        df = df[~df["nOrdNo"].isin(processed_ids)].copy()
        
        if df.empty:
            _print_summary(0, banked_pnl)
            return pd.DataFrame(), pd.DataFrame()

        df["qty"] = pd.to_numeric(df["fldQty"]).fillna(0)
        df["prc"] = pd.to_numeric(df["avgPrc"]).fillna(0)
        df["dt"] = pd.to_datetime(df["ordDtTm"])
        df = df.sort_values(by="dt")

        closed_matches = []
        open_positions = []

        for symbol, group in df.groupby("trdSym"):
            token_id = group["tok"].iloc[0]
            ex_seg = group["exSeg"].iloc[0]
            buys = group[group["trnsTp"].str.upper() == "B"].to_dict('records')
            sells = group[group["trnsTp"].str.upper() == "S"].to_dict('records')

            for s in sells:
                while s["qty"] > 0 and buys:
                    if MATCH_MODE == "PFO":
                        buys.sort(key=lambda x: (s["prc"] - x["prc"]), reverse=True)
                    
                    b = buys[0]
                    mqty = min(s["qty"], b["qty"])
                    pnl_val = int((s["prc"] - b["prc"]) * mqty)
                    
                    if pnl_val > 0: banked_pnl += pnl_val
                    
                    processed_ids.add(s["nOrdNo"])
                    processed_ids.add(b["nOrdNo"])
                    
                    s["qty"] -= mqty
                    b["qty"] -= mqty
                    if b["qty"] <= 0: buys.pop(0)

            # --- CRITICAL FIX: Keeping original naming for downstream ---
            for rem in buys:
                if rem["qty"] > 0:
                    live_val = get_mid_price(client, token_id, ex_seg)
                    open_positions.append({
                        "symbol": symbol,           # Dashboard needs 'symbol'
                        "qty": rem["qty"],
                        "pxy_entry": rem["prc"],    # Changed from 'prc' to 'pxy_entry'
                        "sell_prc": live_val,      # Changed from 'live_val' to 'sell_prc'
                        "pnl": int((live_val - rem["prc"]) * rem["qty"])
                    })

        open_df = pd.DataFrame(open_positions)
        total_unrealized = int(open_df["pnl"].sum()) if not open_df.empty else 0
        
        _print_summary(total_unrealized, banked_pnl)
        dump_to_json(banked_pnl, processed_ids)
        return open_df, pd.DataFrame()
        
    except Exception as e:
        print(f"[LILO ERROR]: {e}")
        return pd.DataFrame(), pd.DataFrame()

def _print_summary(total_unrealized, total_realized):
    from colorama import Fore, Style
    color = Style.BRIGHT + Fore.GREEN if total_realized >= 0 else Fore.RED
    print(f"\n 🏃 {int(total_unrealized):+06d} 🔸 🥅 {color}{int(total_realized):+06d}{Style.RESET_ALL} 🥅\n")



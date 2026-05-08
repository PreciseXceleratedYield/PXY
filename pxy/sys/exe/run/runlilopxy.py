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
PNL_FILE = os.path.expanduser("~/pxy/pnl.json")
META_FILE = os.path.expanduser("~/pxy/pnl_meta.json")

def rotate_daily_file():
    """Archives pnl files at market open to start fresh daily."""
    try:
        if not os.path.exists(PNL_FILE): return
        now = datetime.now()
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        mtime = datetime.fromtimestamp(os.path.getmtime(PNL_FILE))
        if now >= market_open and mtime < market_open:
            date_str = mtime.strftime("%Y-%m-%d")
            for f in [PNL_FILE, META_FILE]:
                if os.path.exists(f):
                    os.rename(f, f.replace(".json", f"_{date_str}.json"))
    except: pass

def dump_data(closed_df, banked_pnl, processed_ids):
    """Maintains original pnl.json format and saves internal state to meta."""
    try:
        # 1. Save pnl.json exactly as original (List of records)
        trade_data = []
        if not closed_df.empty:
            records = closed_df.copy()
            for col in records.columns:
                if pd.api.types.is_datetime64_any_dtype(records[col]):
                    records[col] = records[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            trade_data = records.to_dict(orient='records')
        
        with open(PNL_FILE, "w") as f:
            json.dump(trade_data, f, indent=4)

        # 2. Save internal logic state to meta file
        meta_data = {
            "banked_pnl": int(banked_pnl),
            "processed_ids": list(processed_ids)
        }
        with open(META_FILE, "w") as f:
            json.dump(meta_data, f, indent=4)
    except: pass

def process_lilo_orders(client):
    try:
        rotate_daily_file()
        
        # Load memory from meta file
        banked_pnl, processed_ids = 0, set()
        if os.path.exists(META_FILE):
            with open(META_FILE, "r") as f:
                meta = json.load(f)
                banked_pnl = meta.get("banked_pnl", 0)
                processed_ids = set(meta.get("processed_ids", []))

        res = client.order_report()
        if not res or "data" not in res: return pd.DataFrame(), pd.DataFrame()

        df = pd.DataFrame(res["data"])
        df = df[df["ordSt"].isin(["complete", "traded"])].copy()
        
        # Filter out orders we have already processed in previous runs
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
                    # 🔁 PFO: Sort buys to pick the one that gives maximum profit vs current sell
                    if MATCH_MODE == "PFO":
                        buys.sort(key=lambda x: (s["prc"] - x["prc"]), reverse=True)
                    
                    b = buys[0]
                    mqty = min(s["qty"], b["qty"])
                    pnl_val = int((s["prc"] - b["prc"]) * mqty)
                    
                    if pnl_val > 0: banked_pnl += pnl_val
                    processed_ids.add(s["nOrdNo"])
                    processed_ids.add(b["nOrdNo"])
                    
                    closed_matches.append({
                        "Symbol": symbol, "Qty": mqty, "tok": token_id,
                        "Buy_Time": b["dt"], "Buy_Prc": b["prc"],
                        "Exit_Time": s["dt"], "Sell_Prc": s["prc"], "PNL": pnl_val
                    })
                    
                    s["qty"] -= mqty
                    b["qty"] -= mqty
                    if b["qty"] <= 0: buys.pop(0)

            for rem in buys:
                if rem["qty"] > 0:
                    live_val = get_mid_price(client, token_id, ex_seg)
                    open_positions.append({
                        "Symbol": symbol, "Qty": rem["qty"], "tok": token_id,
                        "Buy_Time": rem["dt"], "Buy_Prc": rem["prc"],
                        "Exit_Time": "OPEN", "Sell_Prc": live_val,
                        "PNL": int((live_val - rem["prc"]) * rem["qty"])
                    })

        open_df = pd.DataFrame(open_positions)
        closed_df = pd.DataFrame(closed_matches)
        
        total_unrealized = int(open_df["PNL"].sum()) if not open_df.empty else 0
        _print_summary(total_unrealized, banked_pnl)
        
        dump_data(closed_df, banked_pnl, processed_ids)
        return open_df, closed_df
        
    except Exception as e:
        print(f"[LILO ERROR]: {e}")
        return pd.DataFrame(), pd.DataFrame()

def _print_summary(total_unrealized, total_realized):
    from colorama import Fore, Style, init
    init(autoreset=True)
    color = Style.BRIGHT + Fore.GREEN if total_realized >= 0 else Fore.RED
    print(f"\n 🏃 {int(total_unrealized):+06d} 🔸 🥅 {color}{int(total_realized):+06d}{Style.RESET_ALL} 🥅\n")

if __name__ == "__main__":
    client = get_session()
    process_lilo_orders(client)


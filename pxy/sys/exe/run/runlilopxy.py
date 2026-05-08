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

def rotate_daily_file():
    """Archives pnl.json at market open to start fresh daily."""
    try:
        if not os.path.exists(PNL_FILE): return
        now = datetime.now()
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        mtime = datetime.fromtimestamp(os.path.getmtime(PNL_FILE))
        if now >= market_open and mtime < market_open:
            date_str = mtime.strftime("%Y-%m-%d")
            os.rename(PNL_FILE, PNL_FILE.replace(".json", f"_{date_str}.json"))
    except: pass

def dump_to_pnl_json(new_matches):
    """Strictly places all coded/matched trades into pnl.json."""
    try:
        history = []
        if os.path.exists(PNL_FILE):
            with open(PNL_FILE, "r") as f:
                try:
                    history = json.load(f)
                except: history = []

        if not new_matches.empty:
            records = new_matches.copy()
            # Formatting for JSON compatibility
            for col in records.columns:
                if pd.api.types.is_datetime64_any_dtype(records[col]):
                    records[col] = records[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            new_list = records.to_dict(orient='records')
            history.extend(new_list)

        with open(PNL_FILE, "w") as f:
            json.dump(history, f, indent=4)
    except Exception as e:
        print(f"[JSON ERR]: {e}")

def process_lilo_orders(client):
    try:
        rotate_daily_file()
        
        # Load processed IDs from existing PNL file to avoid double-entry
        processed_ids = set()
        if os.path.exists(PNL_FILE):
            with open(PNL_FILE, "r") as f:
                try:
                    for trade in json.load(f):
                        if "buy_id" in trade: processed_ids.add(trade["buy_id"])
                        if "sell_id" in trade: processed_ids.add(trade["sell_id"])
                except: pass

        res = client.order_report()
        if not res or "data" not in res: return pd.DataFrame(), pd.DataFrame()

        df = pd.DataFrame(res["data"])
        df = df[df["ordSt"].isin(["complete", "traded"])].copy()
        df = df[~df["nOrdNo"].isin(processed_ids)].copy()
        
        if df.empty:
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
                    
                    closed_matches.append({
                        "Symbol": symbol,
                        "Qty": mqty,
                        "Buy_Prc": b["prc"],
                        "Sell_Prc": s["prc"],
                        "PNL": int((s["prc"] - b["prc"]) * mqty),
                        "Exit_Time": s["dt"],
                        "buy_id": b["nOrdNo"], # Stored to prevent re-processing
                        "sell_id": s["nOrdNo"]
                    })
                    
                    s["qty"] -= mqty
                    b["qty"] -= mqty
                    if b["qty"] <= 0: buys.pop(0)

            for rem in buys:
                if rem["qty"] > 0:
                    live_val = get_mid_price(client, token_id, ex_seg)
                    open_positions.append({
                        "Symbol": symbol, "Qty": rem["qty"], "Buy_Prc": rem["prc"],
                        "Sell_Prc": live_val, "PNL": int((live_val - rem["prc"]) * rem["qty"])
                    })

        closed_df = pd.DataFrame(closed_matches)
        open_df = pd.DataFrame(open_positions)

        # 💾 SAVE ALL CODED TRADES
        dump_to_pnl_json(closed_df)
        
        return open_df, closed_df
        
    except Exception as e:
        print(f"[LILO ERROR]: {e}")
        return pd.DataFrame(), pd.DataFrame()

if __name__ == "__main__":
    client = get_session()
    process_lilo_orders(client)




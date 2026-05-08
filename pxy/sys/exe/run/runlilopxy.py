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

def dump_to_json(closed_df):
    """Saves closed trades to pnl.json exactly like the original script."""
    try:
        if closed_df.empty:
            data = []
        else:
            records = closed_df.copy()
            # Convert Timestamps to strings for JSON compatibility
            for col in records.columns:
                if pd.api.types.is_datetime64_any_dtype(records[col]):
                    records[col] = records[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            data = records.to_dict(orient='records')
            
        with open(MEMORY_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[DUMP ERROR]: {e}")

def process_lilo_orders(client):
    try:
        if not client:
            _print_summary(0, 0)
            return pd.DataFrame(), pd.DataFrame()

        res = client.order_report()
        if not res or "data" not in res:
            _print_summary(0, 0)
            return pd.DataFrame(), pd.DataFrame()

        df = pd.DataFrame(res["data"])
        df = df[df["ordSt"].isin(["complete", "traded"])].copy()
        
        if df.empty:
            _print_summary(0, 0)
            return pd.DataFrame(), pd.DataFrame()

        # Data Cleaning
        df["qty"] = pd.to_numeric(df["fldQty"], errors='coerce').fillna(0)
        df["prc"] = pd.to_numeric(df["avgPrc"], errors='coerce').fillna(0)
        df["dt"] = pd.to_datetime(df["ordDtTm"])
        df = df.sort_values(by="dt", ascending=True)

        closed_matches = []
        open_positions = []

        for symbol, group in df.groupby("trdSym"):
            token_id = group["tok"].iloc[0]
            ex_seg = group["exSeg"].iloc[0]
            buys = group[group["trnsTp"].str.upper() == "B"].to_dict('records')
            sells = group[group["trnsTp"].str.upper() == "S"].to_dict('records')

            for s in sells:
                while s["qty"] > 0 and buys:
                    # 🔁 PROFIT FIRST OUT SORTING
                    if MATCH_MODE == "PFO":
                        buys.sort(key=lambda x: (s["prc"] - x["prc"]), reverse=True)
                    
                    b = buys[0]
                    mqty = min(s["qty"], b["qty"])
                    
                    closed_matches.append({
                        "Symbol": symbol,
                        "Qty": mqty,
                        "tok": token_id,
                        "Buy_Time": b["dt"],
                        "Buy_Prc": b["prc"],
                        "Exit_Time": s["dt"],
                        "Sell_Prc": s["prc"],
                        "PNL": int((s["prc"] - b["prc"]) * mqty)
                    })
                    
                    s["qty"] -= mqty
                    b["qty"] -= mqty
                    if b["qty"] <= 0:
                        buys.pop(0)

            # Active Positions
            for rem in buys:
                if rem["qty"] > 0:
                    live_val = get_mid_price(client, token_id, ex_seg)
                    open_positions.append({
                        "Symbol": symbol,
                        "Qty": rem["qty"],
                        "tok": token_id,
                        "Buy_Time": rem["dt"],
                        "Buy_Prc": rem["prc"],
                        "Exit_Time": "OPEN",
                        "Sell_Prc": live_val,
                        "PNL": int((live_val - rem["prc"]) * rem["qty"])
                    })

        open_df = pd.DataFrame(open_positions)
        closed_df = pd.DataFrame(closed_matches)
        
        total_unrealized = int(open_df["PNL"].sum()) if not open_df.empty else 0
        total_realized = int(closed_df["PNL"].sum()) if not closed_df.empty else 0
        
        _print_summary(total_unrealized, total_realized)
        
        # 💾 DUMP EXACTLY AS ORIGINAL
        dump_to_json(closed_df)
        
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


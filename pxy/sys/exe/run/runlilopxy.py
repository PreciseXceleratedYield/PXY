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
                try: history = json.load(f)
                except: history = []
        if not new_matches.empty:
            records = new_matches.copy()
            for col in records.columns:
                if pd.api.types.is_datetime64_any_dtype(records[col]):
                    records[col] = records[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            history.extend(records.to_dict(orient='records'))
        with open(PNL_FILE, "w") as f:
            json.dump(history, f, indent=4)
    except: pass

def _print_summary(total_unrealized, total_realized):
    """Restores the EXACT emoji print format requested."""
    from colorama import Fore, Style, init
    init(autoreset=True)
    
    # Format strings
    unreal_str = f"{int(total_unrealized):+06d}"
    real_str = f"{int(total_realized):+06d}"
    
    # Color logic for goalpost (booked PnL)
    color = Style.BRIGHT + Fore.GREEN if total_realized >= 0 else Fore.RED
    
    # Exact original layout: 🏃 Unrel 🔸 🥅 Real 🥅
    part1 = f"🥅 {color}{real_str}{Style.RESET_ALL} 🥅"
    part2 = f" {unreal_str} 🔸 🏃‍♂️ 🔸 🏃‍♂️"
    combined = f" {part2} {part1}"
    
    print()
    print(f"{combined:^38}")
    print()

def process_lilo_orders(client):
    try:
        rotate_daily_file()
        
        # Load processed IDs and calculate current Booked PnL
        booked_total = 0
        processed_ids = set()
        if os.path.exists(PNL_FILE):
            with open(PNL_FILE, "r") as f:
                try:
                    hist = json.load(f)
                    for t in hist:
                        booked_total += int(t.get("PNL", 0))
                        if "buy_id" in t: processed_ids.add(t["buy_id"])
                        if "sell_id" in t: processed_ids.add(t["sell_id"])
                except: pass

        res = client.order_report()
        if not res or "data" not in res: 
            _print_summary(0, booked_total)
            return pd.DataFrame(), pd.DataFrame()

        df = pd.DataFrame(res["data"])
        df = df[df["ordSt"].isin(["complete", "traded"])].copy()
        df = df[~df["nOrdNo"].isin(processed_ids)].copy()
        
        if df.empty:
            _print_summary(0, booked_total)
            return pd.DataFrame(), pd.DataFrame()

        df["qty"] = pd.to_numeric(df["fldQty"]).fillna(0)
        df["prc"] = pd.to_numeric(df["avgPrc"]).fillna(0)
        df["dt"] = pd.to_datetime(df["ordDtTm"])
        df = df.sort_values(by="dt")

        closed_matches, open_positions = [], []

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
                    pnl = int((s["prc"] - b["prc"]) * mqty)
                    
                    booked_total += pnl
                    closed_matches.append({
                        "Symbol": symbol, "Qty": mqty, "Buy_Prc": b["prc"],
                        "Sell_Prc": s["prc"], "PNL": pnl, "Exit_Time": s["dt"],
                        "buy_id": b["nOrdNo"], "sell_id": s["nOrdNo"]
                    })
                    
                    s["qty"] -= mqty
                    b["qty"] -= mqty
                    if b["qty"] <= 0: buys.pop(0)

            for rem in buys:
                if rem["qty"] > 0:
                    live_val = get_mid_price(client, token_id, ex_seg)
                    open_positions.append({
                        "Symbol": symbol, "Qty": rem["qty"], "PNL": int((live_val - rem["prc"]) * rem["qty"])
                    })

        closed_df = pd.DataFrame(closed_matches)
        open_df = pd.DataFrame(open_positions)
        
        running_total = open_df["PNL"].sum() if not open_df.empty else 0
        
        # Output visual summary before saving
        _print_summary(running_total, booked_total)

        dump_to_pnl_json(closed_df)
        return open_df, closed_df

    except Exception as e:
        print(f"[LILO ERROR]: {e}")
        return pd.DataFrame(), pd.DataFrame()

if __name__ == "__main__":
    client = get_session()
    process_lilo_orders(client)



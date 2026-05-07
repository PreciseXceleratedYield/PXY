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
MATCH_MODE = "PFO"  # Profit First Out: Targets maximum win lots first
MEMORY_FILE = os.path.expanduser("~/pxy/pnl.json")

def rotate_daily_file():
    """Archives old pnl.json at the first run after 9:15 AM IST every day."""
    try:
        if not os.path.exists(MEMORY_FILE):
            return
        
        now = datetime.now()
        # Today's 9:15 AM Cutoff
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        
        # Get the file's last modified time
        mtime = datetime.fromtimestamp(os.path.getmtime(MEMORY_FILE))
        
        # If it's after 9:15 AM today, but the file was last updated before today's 9:15 AM
        if now >= market_open and mtime < market_open:
            date_str = mtime.strftime("%Y-%m-%d")
            archive_path = MEMORY_FILE.replace(".json", f"_{date_str}.json")
            os.rename(MEMORY_FILE, archive_path)
            print(f"\n☀️  NEW DAY: Archived yesterday's PnL to {os.path.basename(archive_path)}")
    except Exception as e:
        print(f"[ROTATION ERROR]: {e}")

def dump_to_json(banked_pnl, processed_ids):
    """Saves banked wins and order IDs to memory."""
    try:
        data = {
            "banked_pnl": int(banked_pnl),
            "processed_ids": list(processed_ids)
        }
        with open(MEMORY_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except:
        pass

def process_lilo_orders(client):
    try:
        # 1. HANDLE DAILY RESET
        rotate_daily_file()

        # 2. LOAD EXISTING MEMORY
        banked_pnl = 0
        processed_ids = set()
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r") as f:
                try:
                    hist = json.load(f)
                    banked_pnl = hist.get("banked_pnl", 0)
                    processed_ids = set(hist.get("processed_ids", []))
                except: pass

        if not client:
            _print_summary(0, banked_pnl)
            return pd.DataFrame(), pd.DataFrame()

        # 3. GET ORDERS & FILTER PROCESSED IDS
        res = client.order_report()
        if not res or "data" not in res:
            _print_summary(0, banked_pnl)
            return pd.DataFrame(), pd.DataFrame()

        df = pd.DataFrame(res["data"])
        df = df[df["ordSt"].isin(["complete", "traded"])].copy()
        
        # Filter: Only process orders the script hasn't seen before
        df = df[~df["nOrdNo"].isin(processed_ids)].copy()

        if df.empty:
            _print_summary(0, banked_pnl)
            return pd.DataFrame(), pd.DataFrame()

        df["qty"] = pd.to_numeric(df["fldQty"], errors='coerce').fillna(0)
        df["prc"] = pd.to_numeric(df["avgPrc"], errors='coerce').fillna(0)
        df["dt"] = pd.to_datetime(df["ordDtTm"])
        df = df.sort_values(by="dt", ascending=True)

        closed_matches = []
        open_positions = []

        # 4. PFO MATCHING ENGINE
        for symbol, group in df.groupby("trdSym"):
            token_id = group["tok"].iloc[0]
            ex_seg = group["exSeg"].iloc[0]
            
            buys = group[group["trnsTp"].str.upper() == "B"].to_dict('records')
            sells = group[group["trnsTp"].str.upper() == "S"].to_dict('records')

            for s in sells:
                while s["qty"] > 0 and buys:
                    # Profit First Out Sorting
                    if MATCH_MODE == "PFO":
                        buys.sort(key=lambda x: (s["prc"] - x["prc"]), reverse=True)
                    elif MATCH_MODE == "LIFO":
                        buys.sort(key=lambda x: x["dt"], reverse=True)
                    else: # FIFO
                        buys.sort(key=lambda x: x["dt"], reverse=False)

                    b = buys[0]
                    mqty = min(s["qty"], b["qty"])
                    pnl_val = int((s["prc"] - b["prc"]) * mqty)

                    # Update Banked PnL (Requirement: Accumulate positive profit only)
                    if pnl_val > 0: 
                        banked_pnl += pnl_val

                    closed_matches.append({
                        "Symbol": symbol, "Qty": mqty, "PNL": pnl_val,
                        "Exit_Time": s["dt"]
                    })
                    
                    # Mark IDs as used so they survive restart and don't kill new trades
                    processed_ids.add(s["nOrdNo"])
                    processed_ids.add(b["nOrdNo"])

                    s["qty"] -= mqty
                    b["qty"] -= mqty
                    if b["qty"] <= 0: buys.pop(0)

            # 5. REMAINING ACTIVE INDEPENDENT POSITIONS
            for rem in buys:
                if rem["qty"] > 0:
                    live_val = get_mid_price(client, token_id, ex_seg)
                    open_positions.append({
                        "Symbol": symbol, "Qty": rem["qty"],
                        "PNL": int((live_val - rem["prc"]) * rem["qty"])
                    })

        open_df = pd.DataFrame(open_positions)
        total_unrealized = int(open_df["PNL"].sum()) if not open_df.empty else 0
        
        # 6. OUTPUT & SAVE
        _print_summary(total_unrealized, banked_pnl)
        dump_to_json(banked_pnl, processed_ids)
        
        return open_df, pd.DataFrame(closed_matches)

    except Exception as e:
        print(f"[LILO ERROR]: {e}")
        return pd.DataFrame(), pd.DataFrame()

def _print_summary(total_unrealized, total_realized):
    """Prints emoji summary on a single line."""
    from colorama import Fore, Style, init
    init(autoreset=True)
    color = Style.BRIGHT + Fore.GREEN if total_realized >= 0 else Fore.RED
    line = f" 🏃‍♂️ {int(total_unrealized):+06d}  🔸  🥅 {color}{int(total_realized):+06d}{Style.RESET_ALL} 🥅"
    print(f"\n{line:^40}\n")

if __name__ == "__main__":
    client = get_session()
    process_lilo_orders(client)



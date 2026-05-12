# run/runlilopxy.py
import pandas as pd
import json
import os
from runclntpxy import get_session
from runltpspxy import get_mid_price

# =========================
# ⚙️ CONFIGURATION
# =========================
MATCH_MODE = "TAG" # Switched from PFO to Tag-Based (HHMMSS)

def dump_to_json(closed_df):
    """Saves closed trades to pnl.json in ~/pxy/."""
    try:
        file_path = os.path.expanduser("~/pxy/pnl.json")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if closed_df.empty:
            data = []
        else:
            records = closed_df.copy()
            for col in records.columns:
                if pd.api.types.is_datetime64_any_dtype(records[col]):
                    records[col] = records[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            data = records.to_dict(orient='records')
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
    except:
        pass

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
        # Filtering for completed orders
        df = df[df["ordSt"].isin(["complete", "traded"])].copy()
        
        if df.empty:
            _print_summary(0, 0)
            return pd.DataFrame(), pd.DataFrame()

        # Data Cleaning
        df["qty"] = pd.to_numeric(df["fldQty"], errors='coerce').fillna(0)
        df["prc"] = pd.to_numeric(df["avgPrc"], errors='coerce').fillna(0)
        df["dt"] = pd.to_datetime(df["ordDtTm"])

        # SAFE TAG EXTRACTION: Handles missing guiOrdId for old orders
        # Replace your existing get_safe_tag with this:
        def get_safe_tag(row):
            # Get value and force to string, remove '.0' if it's a float
            t = row.get("guiOrdId") or row.get("tag") or ""
            t_str = str(t).split('.')[0].strip() # Clean float .0
            return t_str if t_str.lower() not in ["nan", "none", ""] else ""


        df["tag"] = df.apply(get_safe_tag, axis=1)

        closed_matches = []
        open_positions = []

        for symbol, group in df.groupby("trdSym"):
            token_id = group["tok"].iloc[0]
            ex_seg = group["exSeg"].iloc[0]
            
            buys = group[group["trnsTp"].str.upper() == "B"].to_dict('records')
            sells = group[group["trnsTp"].str.upper() == "S"].to_dict('records')

            # =========================
            # 🔁 TAG-MATCHING ENGINE (HHMMSS)
            # =========================
            matched_sell_indices = []
            
            for b in buys:
                # RULE: If Buy has NO TAG (Old Bag), it cannot be matched by this logic
                if b["tag"] == "":
                    continue

                # Look for a sell with the EXACT same tag (HHMMSS)
                match_idx = next((i for i, s in enumerate(sells) 
                                 if s["tag"] == b["tag"] 
                                 and i not in matched_sell_indices), None)
                
                if match_idx is not None:
                    s = sells[match_idx]
                    matched_sell_indices.append(match_idx)
                    
                    mqty = min(s["qty"], b["qty"])
                    closed_matches.append({
                        "Symbol": symbol,
                        "Qty": mqty,
                        "Tag": b["tag"],
                        "tok": token_id,
                        "Buy_Time": b["dt"],
                        "Buy_Prc": b["prc"],
                        "Exit_Time": s["dt"],
                        "Sell_Prc": s["prc"],
                        "PNL": int((s["prc"] - b["prc"]) * mqty)
                    })
                    b["qty"] -= mqty # Mark as matched
                
            # Remaining Buys (Untagged OLD bags OR unmatched new scalps) go to Open
            for b in buys:
                if b["qty"] > 0:
                    live_val = get_mid_price(client, token_id, ex_seg)
                    open_positions.append({
                        "Symbol": symbol,
                        "Qty": b["qty"],
                        "tok": token_id,
                        "tag": b["tag"], 
                        "Buy_Time": b["dt"],
                        "Buy_Prc": b["prc"],
                        "Exit_Time": "OPEN",
                        "Sell_Prc": live_val,
                        "PNL": int((live_val - b["prc"]) * b["qty"])
                    })

        open_df = pd.DataFrame(open_positions)
        closed_df = pd.DataFrame(closed_matches)
        
        total_unrealized = int(open_df["PNL"].sum()) if not open_df.empty else 0
        total_realized = int(closed_df["PNL"].sum()) if not closed_df.empty else 0

        _print_summary(total_unrealized, total_realized)
        dump_to_json(closed_df)
        
        return open_df, closed_df

    except Exception as e:
        print(f"[TAG MATCH ERROR]: {e}")
        _print_summary(0, 0)
        return pd.DataFrame(), pd.DataFrame()

def _print_summary(total_unrealized, total_realized):
    from colorama import Fore, Style, init
    init(autoreset=True)
    color = Style.BRIGHT + Fore.GREEN if total_realized >= 0 else Fore.RED
    unreal_str = f"{int(total_unrealized):+06d}"
    real_str = f"{int(total_realized):+06d}"
    print(f"\n {unreal_str} 🔸 🏃‍♂️ 🔸 🏃‍♂️   🥅 {color}{real_str}{Style.RESET_ALL} 🥅\n")

if __name__ == "__main__":
    client = get_session()
    process_lilo_orders(client)



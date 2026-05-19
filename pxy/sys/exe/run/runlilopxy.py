# run/runlilopxy.py 
import pandas as pd 
import json 
import os 
from runclntpxy import get_session 
from runltpspxy import get_mid_price 

MATCH_MODE = "TAG" 

def dump_to_json(closed_df): 
    try: 
        file_path = os.path.expanduser("~/pxy/pnl.json") 
        print(f"[DEBUG] [dump_to_json] Target JSON file path resolved to: {file_path}")
        os.makedirs(os.path.dirname(file_path), exist_ok=True) 
        if closed_df.empty: 
            print("[DEBUG] [dump_to_json] closed_df is empty. Dumping empty array.")
            data = [] 
        else: 
            print(f"[DEBUG] [dump_to_json] Formatting closed_df with {len(closed_df)} rows.")
            records = closed_df.copy() 
            for col in records.columns: 
                if pd.api.types.is_datetime64_any_dtype(records[col]): 
                    records[col] = records[col].dt.strftime('%Y-%m-%d %H:%M:%S') 
            data = records.to_dict(orient='records') 
        with open(file_path, "w") as f: 
            json.dump(data, f, indent=4) 
        print("[DEBUG] [dump_to_json] Successfully wrote structural data to JSON.")
    except Exception as e: 
        print(f"Error dumping to JSON: {e}") 

def process_lilo_orders(client): 
    try: 
        print("[DEBUG] [process_lilo_orders] Function started.")
        if not client: 
            print("[DEBUG] [process_lilo_orders] CRITICAL: client object is None.")
            _print_summary(0, 0) 
            return pd.DataFrame(), pd.DataFrame() 
            
        print("[DEBUG] [process_lilo_orders] Sending API request to client.order_report()...")
        res = client.order_report() 
        print(f"[DEBUG] [process_lilo_orders] Received order report response. Type: {type(res)}")
        
        if not res or "data" not in res: 
            print("[DEBUG] [process_lilo_orders] WARNING: order_report response empty or lacks 'data' key.")
            _print_summary(0, 0) 
            return pd.DataFrame(), pd.DataFrame() 
            
        print(f"[DEBUG] [process_lilo_orders] Orders array length in raw data: {len(res['data'])}")
        df = pd.DataFrame(res["data"]) 
        print(f"[DEBUG] [process_lilo_orders] Columns available in dataframe: {list(df.columns)}")
        
        df = df[df["ordSt"].isin(["complete", "traded"])].copy() 
        print(f"[DEBUG] [process_lilo_orders] Filtered for complete/traded orders. Remaining rows: {len(df)}")
        if df.empty: 
            _print_summary(0, 0) 
            return pd.DataFrame(), pd.DataFrame() 
            
        df["qty"] = pd.to_numeric(df["fldQty"], errors='coerce').fillna(0) 
        df["prc"] = pd.to_numeric(df["avgPrc"], errors='coerce').fillna(0) 
        df["dt"] = pd.to_datetime(df["ordDtTm"]) 

        # FIX: Standardized parser that accurately extracts base tags from _S markers
        def get_safe_tag(row): 
            t = row.get("GuiOrdId") or row.get("guiOrdId") or row.get("tag") or row.get("memo") or "" 
            # First clean potential decimal points from floats
            t_str = str(t).split('.')[0].strip() 
            # Split off the explicit _S identifier flag to isolate the raw base token
            if "_S" in t_str:
                t_str = t_str.split('_S')[0].strip()
            elif "_" in t_str:
                t_str = t_str.split('_')[0].strip()
            return t_str if t_str.lower() not in ["nan", "none", "null", ""] else "" 
            
        df["tag"] = df.apply(get_safe_tag, axis=1) 
        closed_matches = [] 
        open_positions = [] 

        print(f"[DEBUG] [process_lilo_orders] Beginning processing groupby grouping by symbol. Unique symbols: {df['trdSym'].nunique()}")
        for symbol, group in df.groupby("trdSym"): 
            token_id = group["tok"].iloc[0] 
            ex_seg = group["exSeg"].iloc[0] 
            buys = group[group["trnsTp"].str.upper() == "B"].to_dict('records') 
            sells = group[group["trnsTp"].str.upper() == "S"].to_dict('records') 
            matched_sell_indices = set() 
            print(f"[DEBUG] [Group: {symbol}] Processing. Buys count: {len(buys)} | Sells count: {len(sells)}")
            
            for b in buys: 
                if not b["tag"]: 
                    continue 
                match_idx = next((i for i, s in enumerate(sells) if s["tag"] != "" and s["tag"].startswith(b["tag"]) and i not in matched_sell_indices), None) 
                if match_idx is not None: 
                    s = sells[match_idx] 
                    matched_sell_indices.add(match_idx) 
                    mqty = min(s["qty"], b["qty"]) 
                    print(f"[DEBUG] [Group: {symbol}] MATCH FOUND for tag {b['tag']}. Matched Qty: {mqty}")
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
                    b["qty"] -= mqty 

            for b in buys: 
                if b["qty"] > 0: 
                    print(f"[DEBUG] [Group: {symbol}] Found open position balance qty: {b['qty']}. Requesting market price for token: {token_id}...")
                    live_val = get_mid_price(client, token_id, ex_seg) 
                    print(f"[DEBUG] [Group: {symbol}] get_mid_price returned: {live_val}")
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
                    b["qty"] = 0  # ✅ FIXED: Zeroing balance breaks the tracking freeze instantly

        print(f"[DEBUG] [process_lilo_orders] Finished loops. Open items total: {len(open_positions)} | Closed items total: {len(closed_matches)}")
        open_df = pd.DataFrame(open_positions) 
        closed_df = pd.DataFrame(closed_matches) 
        total_unrealized = int(open_df["PNL"].sum()) if not open_df.empty else 0 
        total_realized = int(closed_df["PNL"].sum()) if not closed_df.empty else 0 
        
        print(f"[DEBUG] [process_lilo_orders] Summary Totals calculated -> Unrealized: {total_unrealized}, Realized: {total_realized}")
        _print_summary(total_unrealized, total_realized) 
        
        print("[DEBUG] [process_lilo_orders] Triggering dump_to_json block...")
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
    print(f"\n {unreal_str} 🔸 🏃‍♂️ 🔸 🏃‍♂️ 🥅  {color}{real_str}{Style.RESET_ALL} 🥅\n") 

if __name__ == "__main__": 
    print("[DEBUG] [__main__] Initializing session via get_session()...")
    client = get_session() 
    print(f"[DEBUG] [__main__] get_session finished. Client initial status: {'Connected' if client else 'None'}")
    process_lilo_orders(client)


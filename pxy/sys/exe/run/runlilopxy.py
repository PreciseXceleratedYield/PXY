import pandas as pd 
import json 
import os 
from datetime import datetime
from colorama import init, Fore, Style 
from runclntpxy import get_session 
from runltpspxy import get_mid_price 

# Initialize colorama for colored console logs
init(autoreset=True) 

MATCH_MODE = "TAG" 
DEBUG_MODE = False 

def debug_log(msg, color=Fore.BLUE): 
    if DEBUG_MODE: 
        print(f"{color}[DEBUG LILO] {msg}{Style.RESET_ALL}") 

def dump_to_json(closed_df): 
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
        debug_log(f"PNL metrics written successfully to json database ({len(data)} records)", Fore.GREEN)
    except Exception as e: 
        print(f"{Fore.RED}Error dumping to JSON: {e}") 

def process_lilo_orders(client): 
    try: 
        if not client: 
            debug_log("Execution rejected: Client session instance is missing or invalid.", Fore.RED)
            _print_summary(0, 0) 
            return pd.DataFrame(), pd.DataFrame() 
            
        res = client.order_report() 
        if not res or "data" not in res: 
            debug_log("Broker connection returned an empty orderbook or invalid response format.", Fore.RED)
            _print_summary(0, 0) 
            return pd.DataFrame(), pd.DataFrame() 
            
        df = pd.DataFrame(res["data"]) 
        raw_count = len(df)
        df = df[df["ordSt"].isin(["complete", "traded"])].copy() 
        
        debug_log(f"Order report isolated. Raw entries: {raw_count} | Filled/Traded items: {len(df)}", Fore.CYAN)
        
        if df.empty: 
            _print_summary(0, 0) 
            return pd.DataFrame(), pd.DataFrame() 
            
        df["qty"] = pd.to_numeric(df["fldQty"], errors='coerce').fillna(0) 
        df["prc"] = pd.to_numeric(df["avgPrc"], errors='coerce').fillna(0) 
        df["dt"] = pd.to_datetime(df["ordDtTm"]) 

        # Standardized parser that accurately extracts base tags from _S markers
        def get_safe_tag(row): 
            t = row.get("GuiOrdId") or row.get("guiOrdId") or row.get("tag") or row.get("memo") or "" 
            t_str = str(t).split('.')[0].strip() 
            
            # Unmask identifiers
            if "_S" in t_str:
                parsed_tag = t_str.split('_S')[0].strip()
            elif "_" in t_str:
                parsed_tag = t_str.split('_')[0].strip()
            else:
                parsed_tag = t_str
                
            out_tag = parsed_tag if parsed_tag.lower() not in ["nan", "none", "null", ""] else "" 
            return out_tag
            
        df["tag"] = df.apply(get_safe_tag, axis=1) 
        closed_matches = [] 
        open_positions = [] 

        print(f"\n{Fore.WHITE}{'='*60}")
        print(f"{Fore.YELLOW}🚀 EXECUTING LILO ORDER MATCH MATRIX")
        print(f"{Fore.WHITE}{'='*60}")

        for symbol, group in df.groupby("trdSym"): 
            token_id = group["tok"].iloc[0] 
            ex_seg = group["exSeg"].iloc[0] 
            buys = group[group["trnsTp"].str.upper() == "B"].to_dict('records') 
            sells = group[group["trnsTp"].str.upper() == "S"].to_dict('records') 
            matched_sell_indices = set() 
            
            debug_log(f"Analyzing ticker: {symbol:<18} | Buy items: {len(buys)} | Sell items: {len(sells)}", Fore.MAGENTA)
            
            for b in buys: 
                if not b["tag"]: 
                    debug_log(f"  ⚠️ Skipping orphan Buy item without valid order tracking token", Fore.YELLOW)
                    continue 
                
                # Trace logic resolution path
                match_idx = next((i for i, s in enumerate(sells) if s["tag"] != "" and s["tag"].startswith(b["tag"]) and i not in matched_sell_indices), None) 
                
                if match_idx is not None: 
                    s = sells[match_idx] 
                    matched_sell_indices.add(match_idx) 
                    mqty = min(s["qty"], b["qty"]) 
                    pnl_calc = int((s["prc"] - b["prc"]) * mqty)
                    
                    debug_log(f"  {Fore.GREEN}➕ MATCHED SUCCESSFULLY! Tag: {b['tag']} | Qty Matched: {mqty} | PNL: {pnl_calc:+d}")
                    
                    closed_matches.append({ 
                        "Symbol": symbol, 
                        "Qty": mqty, 
                        "Tag": b["tag"], 
                        "tok": token_id, 
                        "Buy_Time": b["dt"], 
                        "Buy_Prc": b["prc"], 
                        "Exit_Time": s["dt"], 
                        "Sell_Prc": s["prc"], 
                        "PNL": pnl_calc 
                    }) 
                    b["qty"] -= mqty 
                else:
                    debug_log(f"  {Fore.YELLOW}⏳ No immediate closing trade counterpart found for tag: {b['tag']}")

            # FIX: Isolate lingering open risks with an explicit LTP safety fallback limit
            for b in buys: 
                if b["qty"] > 0: 
                    # Attempt to fetch dynamic dynamic mid price execution data
                    live_val = get_mid_price(client, token_id, ex_seg) 
                    
                    # LTP Fallback Activation Check
                    if live_val <= 0:
                        debug_log(f"  ⚠️ Mid-price feed failed (0.0) for token {token_id}. Falling back to buy price LTP reference.", Fore.YELLOW)
                        live_val = b["prc"]
                    
                    unrealized_pnl = int((live_val - b["prc"]) * b["qty"])
                    
                    debug_log(f"  🏃 Open tracking detected | Tag: {b['tag']} | Unfilled volume: {b['qty']} | Live LTP: {live_val}")
                    
                    open_positions.append({ 
                        "Symbol": symbol, 
                        "Qty": b["qty"], 
                        "tok": token_id, 
                        "tag": b["tag"], 
                        "Buy_Time": b["dt"], 
                        "Buy_Prc": b["prc"], 
                        "Exit_Time": "OPEN", 
                        "Sell_Prc": live_val, 
                        "PNL": unrealized_pnl 
                    }) 

        print(f"{Fore.WHITE}{'='*60}\n")

        open_df = pd.DataFrame(open_positions) 
        closed_df = pd.DataFrame(closed_matches) 
        
        total_unrealized = int(open_df["PNL"].sum()) if not open_df.empty else 0 
        total_realized = int(closed_df["PNL"].sum()) if not closed_df.empty else 0 
        
        _print_summary(total_unrealized, total_realized) 
        dump_to_json(closed_df) 
        return open_df, closed_df 
        
    except Exception as e: 
        print(f"{Fore.RED}[TAG MATCH ERROR CRITICAL CRASH]: {e}") 
        _print_summary(0, 0) 
        return pd.DataFrame(), pd.DataFrame() 

def _print_summary(total_unrealized, total_realized): 
    color = Style.BRIGHT + Fore.GREEN if total_realized >= 0 else Fore.RED 
    unreal_str = f"{int(total_unrealized):+06d}" 
    real_str = f"{int(total_realized):+06d}" 
    print(f"\n {unreal_str} 🔸 🏃‍♂️ 🔸 🏃‍♂️ 🥅  {color}{real_str}{Style.RESET_ALL} 🥅\n") 

if __name__ == "__main__": 
    client = get_session() 
    process_lilo_orders(client)


# run/runlilopxy.py 
import pandas as pd 
import json 
import os 
from colorama import init, Fore, Style 
from runclntpxy import get_session 
from runltpspxy import get_mid_price 

# Initialize colorama for colored console logs
init(autoreset=True) 

MATCH_MODE = "TAG" 
DEBUG_MODE = True 

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
        df = df[df["ordSt"].isin(["complete", "traded"])].copy() 
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
            if "_S" in t_str:
                t_str = t_str.split('_S').strip()
            elif "_" in t_str:
                t_str = t_str.split('_').strip()
            return t_str if t_str.lower() not in ["nan", "none", "null", ""] else "" 
            
        df["tag"] = df.apply(get_safe_tag, axis=1) 
        closed_matches = [] 
        open_positions = [] 

        for symbol, group in df.groupby("trdSym"): 
            # Fix token variations safely to maintain clean numeric strings
            try:
                token_id = str(int(float(str(group["tok"].iloc).split('.').strip())))
            except:
                token_id = str(group["tok"].iloc).strip()

            raw_seg = group["exSeg"].iloc 
            # Kotak Neo V2 internal API requests strictly expect lower-case "nse_fo" parameter wrappers
            ex_seg = "nse_fo" if str(raw_seg).lower() in ["nse_fo", "nfo"] else str(raw_seg).lower()
            
            buys = group[group["trnsTp"].str.upper() == "B"].to_dict('records') 
            sells = group[group["trnsTp"].str.upper() == "S"].to_dict('records') 
            matched_sell_indices = set() 
            
            for b in buys: 
                if not b["tag"]: 
                    continue 
                match_idx = next((i for i, s in enumerate(sells) if s["tag"] != "" and s["tag"].startswith(b["tag"]) and i not in matched_sell_indices), None) 
                if match_idx is not None: 
                    s = sells[match_idx] 
                    matched_sell_indices.add(match_idx) 
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
                    b["qty"] -= mqty 

            # ==============================================================================
            # 🛡️ VERBOSE LIVE VALUATION FETCH ENGINE (KOTAK NEO V2 NATIVE SPECIFICATION)
            # ==============================================================================
            for b in buys: 
                if b["qty"] > 0: 
                    debug_log(f"Fetching Price -> Ticker: {symbol} | Token: {token_id} | Segment: {ex_seg}", Fore.CYAN)
                    
                    # 1. Primary Attempt: Use your local mid price algorithm module mapping
                    live_val = get_mid_price(client, token_id, ex_seg) 
                    debug_log(f"  -> API Response (get_mid_price): {live_val}", Fore.MAGENTA)
                    
                    # 2. Kotak Neo V2 Native Scrip Info Fallback Lookup (Fires if mid-price outputs 0.0)
                    if live_val <= 0:
                        try:
                            # Kotak Neo V2 SDK natively looks up single contracts using client.get_scrip_info
                            scrip_data = client.get_scrip_info(exchangeSegment=ex_seg, instrumentToken=token_id)
                            
                            if scrip_data and isinstance(scrip_data, dict):
                                # Extract real-time last traded price from V2 payload dictionary structure
                                live_val = float(scrip_data.get("ltp") or scrip_data.get("lastTradedPrice") or 0)
                                if live_val > 0:
                                    debug_log(f"  {Fore.GREEN}✅ [KOTAK V2 SUCCESS] Recovered live price using get_scrip_info: {live_val}")
                                    
                            # Alternate list layout safety parsing
                            elif scrip_data and isinstance(scrip_data, list) and len(scrip_data) > 0:
                                inner_block = scrip_data[0]
                                live_val = float(inner_block.get("ltp") or inner_block.get("lastTradedPrice") or 0)
                                if live_val > 0:
                                    debug_log(f"  {Fore.GREEN}✅ [KOTAK V2 SUCCESS] Recovered live price from list packet array: {live_val}")
                        except Exception as v2_err:
                            debug_log(f"  Direct Kotak Neo V2 API dynamic recovery error: {v2_err}", Fore.RED)
                    
                    # 3. Last Resort Safety net (Only defaults to entry if the entire network connection drops)
                    if live_val <= 0:
                        print(f"  {Fore.RED}🚨 [FEED DEAD] Complete fallback network dropout. Defaulting to buy anchor price: {b['prc']}")
                        live_val = b["prc"]
                    
                    unrealized_pnl = int((live_val - b["prc"]) * b["qty"])
                    debug_log(f"  -> Final Assigned Valuation Price: {live_val} | Calculated PNL: {unrealized_pnl:+d}", Fore.GREEN)
                    
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



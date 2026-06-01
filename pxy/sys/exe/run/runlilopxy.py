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

        # Clean tag parser safely extracting base token strings without list split bugs
        def get_safe_tag(row): 
            try:
                t = row.get("GuiOrdId") or row.get("guiOrdId") or row.get("tag") or row.get("memo") or "" 
                t_str = str(t).strip()
                if '.' in t_str:
                    t_str = t_str.split('.')[0].strip()
                if "_S" in t_str:
                    t_str = t_str.split('_S')[0].strip()
                elif "_" in t_str:
                    t_str = t_str.split('_')[0].strip()
                return t_str if t_str.lower() not in ["nan", "none", "null", ""] else "" 
            except Exception:
                return "" 
            
        df["tag"] = df.apply(get_safe_tag, axis=1) 
        closed_matches = [] 
        open_positions = [] 

        for symbol, group in df.groupby("trdSym"): 
            try:
                raw_tok = str(group["tok"].iloc[0]).strip()
                if '.' in raw_tok:
                    raw_tok = raw_tok.split('.')[0].strip()
                token_id = str(int(float(raw_tok)))
            except Exception:
                try:
                    token_id = str(group["tok"].iloc[0]).strip()
                except Exception:
                    token_id = ""

            try:
                raw_seg = str(group["exSeg"].iloc[0]).strip()
            except Exception:
                raw_seg = "nse_fo"
                
            # Kotak Neo V2 native quotes endpoint strictly requires lowercase "nse_fo" parameter tokens
            ex_seg = "nse_fo" if raw_seg.lower() in ["nse_fo", "nfo"] else raw_seg.lower()
            
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
            # 🎯 ROBUST MULTI-LAYERED PRIORITY RESCUE PRICE MATRIX (KOTAK NEO V2)
            # ==============================================================================
            for b in buys: 
                if b["qty"] > 0: 
                    debug_log(f"Fetching Price -> Ticker: {symbol} | Token: {token_id} | Segment: {ex_seg}", Fore.CYAN)
                    
                    # LAYER 1: Try local mid price algorithm
                    live_val = get_mid_price(client, token_id, ex_seg) 
                    debug_log(f"  -> Layer 1 (get_mid_price): {live_val}", Fore.MAGENTA)
                    
                    # LAYER 2: Try active live broker quotes method (Polished parser matching V2 specs)
                    if live_val <= 0 and token_id:
                        try:
                            # Kotak Neo V2 official array dictionary request parameters structure
                            tokens_payload = [{"instrument_token": str(token_id), "exchange_segment": str(ex_seg)}]
                            v2_quotes = client.quotes(instrument_tokens=tokens_payload, quote_type="ltp")
                            
                            # FIX: Multi-type response unwrap engine to prevent layout crashes
                            if isinstance(v2_quotes, list) and len(v2_quotes) > 0:
                                item = v2_quotes[0]
                                live_val = float(item.get("ltp") or item.get("lastTradedPrice") or 0)
                            elif isinstance(v2_quotes, dict):
                                if "message" in v2_quotes:
                                    msg_block = v2_quotes["message"]
                                    if isinstance(msg_block, list) and len(msg_block) > 0:
                                        live_val = float(msg_block[0].get("ltp", 0))
                                    elif isinstance(msg_block, dict):
                                        live_val = float(msg_block.get("ltp", 0))
                                else:
                                    live_val = float(v2_quotes.get("ltp") or v2_quotes.get("lastTradedPrice") or 0)
                                    
                            if live_val > 0:
                                debug_log(f"  {Fore.GREEN}✅ [Layer 2 Success] Extracted exchange LTP price: {live_val}")
                        except Exception as v2_err:
                            debug_log(f"  Layer 2 API rescue error trace: {v2_err}", Fore.RED)
                    
                    # LAYER 3: Try last known row cache LTP
                    if live_val <= 0:
                        row_cache_ltp = float(b.get("sell_prc") or b.get("ltp") or b.get("LTP") or 0)
                        if row_cache_ltp > 0:
                            debug_log(f"  {Fore.YELLOW}⚠️ [Layer 3 Success] API down. Recovered cached row LTP: {row_cache_ltp}")
                            live_val = row_cache_ltp
                    
                    # LAYER 4: Absolute final safety net -> Fall back to Buy Entry Price
                    if live_val <= 0:
                        print(f"  {Fore.RED}🚨 [LAYER 4 SAFETY] No market data resolved. Falling back to buy entry anchor: {b['prc']}")
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


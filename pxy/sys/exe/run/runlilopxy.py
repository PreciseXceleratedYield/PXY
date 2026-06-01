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
            
        df["qty"] = pd.to_numeric(df["fldQty"], errors='coerce').fillna(0) 
        df["prc"] = pd.to_numeric(df["avgPrc"], errors='coerce').fillna(0) 
        df["dt"] = pd.to_datetime(df["ordDtTm"]) 

        # FIXED: Rebuilt text tag parser to strictly eliminate split list string errors
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
                token_id = str(group["tok"].iloc[0]).strip()

            try:
                raw_seg = str(group["exSeg"].iloc[0]).strip()
            except Exception:
                raw_seg = "nse_fo"
                
            # Kotak Neo V2 strictly demands lower-case 'nse_fo' for options routing
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
            # 🛡️ 5-LAYER MULTI-PRIORITY PRICING RESCUE CHAIN MATRIX (KOTAK NEO V2)
            # ==============================================================================
            for b in buys: 
                if b["qty"] > 0: 
                    live_val = 0.0
                    debug_log(f"Pricing Request -> Symbol: {symbol} | Token: {token_id} | Segment: {ex_seg}", Fore.WHITE)
                    
                    # ---------------- LAYER 1: Custom Mid Price Logic ----------------
                    if live_val <= 0:
                        try:
                            live_val = get_mid_price(client, token_id, ex_seg)
                            if live_val > 0:
                                debug_log(f"  -> Layer 1 [MID CALCULATE SUCCESS] Live Price: {live_val}", Fore.GREEN)
                        except Exception as e1:
                            debug_log(f"  Layer 1 Error: {e1}", Fore.RED)
                    
                    # ---------------- LAYER 2: Native Official V2 Quotes List ----------------
                    if live_val <= 0 and token_id:
                        try:
                            tokens_payload = [{"instrument_token": str(token_id), "exchange_segment": str(ex_seg)}]
                            v2_quotes = client.quotes(instrument_tokens=tokens_payload, quote_type="ltp")
                            
                            if isinstance(v2_quotes, dict):
                                data_chunk = v2_quotes.get("data") or v2_quotes.get("message")
                                if isinstance(data_chunk, list) and len(data_chunk) > 0:
                                    live_val = float(data_chunk[0].get("ltp") or data_chunk[0].get("lastTradedPrice") or 0)
                                elif isinstance(data_chunk, dict):
                                    live_val = float(data_chunk.get("ltp") or data_chunk.get("lastTradedPrice") or 0)
                            elif isinstance(v2_quotes, list) and len(v2_quotes) > 0:
                                live_val = float(v2_quotes[0].get("ltp") or v2_quotes[0].get("lastTradedPrice") or 0)
                                
                            if live_val > 0:
                                debug_log(f"  -> Layer 2 [V2 QUOTES NATIVE SUCCESS] Live Price: {live_val}", Fore.GREEN)
                        except Exception as e2:
                            debug_log(f"  Layer 2 Error: {e2}", Fore.RED)

                    # ---------------- LAYER 3: Scrip Master Info Matching ----------------
                    if live_val <= 0 and token_id:
                        try:
                            scrip_res = client.search_scrip(exchangeSegment=ex_seg, instrumentToken=str(token_id))
                            if isinstance(scrip_res, list) and len(scrip_res) > 0:
                                live_val = float(scrip_res[0].get("ltp") or scrip_res[0].get("lastPrice") or 0)
                            elif isinstance(scrip_res, dict):
                                live_val = float(scrip_res.get("ltp") or scrip_res.get("lastPrice") or 0)
                                
                            if live_val > 0:
                                debug_log(f"  -> Layer 3 [V2 SCRIP SEARCH SUCCESS] Live Price: {live_val}", Fore.GREEN)
                        except Exception as e3:
                            debug_log(f"  Layer 3 Error: {e3}", Fore.RED)

                    # ---------------- LAYER 4: REST Client Raw HTTP Backdoor ----------------
                    if live_val <= 0 and token_id and hasattr(client, 'rest_client'):
                        try:
                            header_params = {
                                "Sid": client.configuration.edit_sid,
                                "Auth": client.configuration.edit_token,
                                "Content-Type": "application/x-www-form-urlencoded"
                            }
                            body_params = {
                                "tokens": f"{ex_seg}|{token_id}",
                                "quoteType": "ltp"
                            }
                            URL = client.configuration.get_url_details("view_quotes")
                            resp = client.rest_client.request(url=URL, method='POST', headers=header_params, body=body_params)
                            
                            if resp and hasattr(resp, 'json'):
                                json_out = resp.json()
                                if isinstance(json_out, dict) and "data" in json_out:
                                    items = json_out["data"]
                                    if isinstance(items, list) and len(items) > 0:
                                        live_val = float(items[0].get("ltp") or items[0].get("lastTradedPrice") or 0)
                                    elif isinstance(items, dict):
                                        live_val = float(items.get("ltp") or items.get("lastTradedPrice") or 0)
                                        
                            if live_val > 0:
                                debug_log(f"  -> Layer 4 [REST BACKDOOR SUCCESS] Live Price: {live_val}", Fore.GREEN)

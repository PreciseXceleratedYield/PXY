# run/runlilopxy.py 
import pandas as pd 
import json 
import os 
from runclntpxy import get_session 
from runltpspxy import get_mid_price 

# TIME FILTER PARAMETER
FILTER_TIME = "09:00:00"

MATCH_MODE = "TAG" 

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
        print(f"Error dumping to JSON: {e}") 

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

        # TIME FILTER BLOCK: Ignore trades before the specified time window
        df = df[df["dt"].dt.time >= pd.to_datetime(FILTER_TIME).time()].copy()
        if df.empty: 
            _print_summary(0, 0) 
            return pd.DataFrame(), pd.DataFrame() 

        # SURGICAL FIX: Safely parse individual string elements away from list manipulation errors
        def get_safe_tag(row): 
            t = row.get("GuiOrdId") or row.get("guiOrdId") or row.get("tag") or row.get("memo") or "" 
            t_str = str(t).strip()
            if '.' in t_str:
                t_str = t_str.split('.')[0].strip() 
            if "_S" in t_str:
                t_str = t_str.split('_S')[0].strip()
            elif "_" in t_str:
                t_str = t_str.split('_')[0].strip()
            return t_str if t_str.lower() not in ["nan", "none", "null", ""] else "" 
            
        df["tag"] = df.apply(get_safe_tag, axis=1) 
        closed_matches = [] 
        open_positions = [] 

        for symbol, group in df.groupby("trdSym"): 
            token_id = str(group["tok"].iloc[0]).split('.')[0].strip()
            raw_seg = str(group["exSeg"].iloc[0]).strip()
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

            # SURGICAL FIX: Implemented 5-Tier Fallback Pricing Hierarchy
            for b in buys: 
                if b["qty"] > 0: 
                    live_val = 0.0
                    
                    # Layer 1: Local Mid Price module algorithm
                    try:
                        live_val = get_mid_price(client, token_id, ex_seg)
                    except:
                        pass
                    
                    # Layer 2: Official V2 Client Quotes Array mapping
                    if live_val <= 0:
                        try:
                            t_payload = [{"instrument_token": str(token_id), "exchange_segment": str(ex_seg)}]
                            v2_q = client.quotes(instrument_tokens=t_payload, quote_type="ltp")
                            if isinstance(v2_q, dict):
                                data_chunk = v2_q.get("data") or v2_q.get("message") or v2_q
                                if isinstance(data_chunk, list) and len(data_chunk) > 0:
                                    live_val = float(data_chunk[0].get("ltp") or data_chunk[0].get("lastTradedPrice") or 0)
                                elif isinstance(data_chunk, dict):
                                    live_val = float(data_chunk.get("ltp") or data_chunk.get("lastTradedPrice") or 0)
                            elif isinstance(v2_q, list) and len(v2_q) > 0:
                                live_val = float(v2_q[0].get("ltp") or v2_q[0].get("lastTradedPrice") or 0)
                        except:
                            pass

                    # Layer 3: Master Scrip Search data block query
                    if live_val <= 0:
                        try:
                            scr_res = client.search_scrip(exchangeSegment=ex_seg, instrumentToken=str(token_id))
                            if isinstance(scr_res, list) and len(scr_res) > 0:
                                live_val = float(scr_res[0].get("ltp") or scr_res[0].get("lastPrice") or 0)
                            elif isinstance(scr_res, dict):
                                live_val = float(scr_res.get("ltp") or scr_res.get("lastPrice") or 0)
                        except:
                            pass

                    # Layer 4: Direct REST client HTTP backend backdoor 
                    if live_val <= 0 and hasattr(client, 'rest_client'):
                        try:
                            h_params = {"Sid": client.configuration.edit_sid, "Auth": client.configuration.edit_token, "Content-Type": "application/x-www-form-urlencoded"}
                            b_params = {"tokens": f"{ex_seg}|{token_id}", "quoteType": "ltp"}
                            URL = client.configuration.get_url_details("view_quotes")
                            resp = client.rest_client.request(url=URL, method='POST', headers=h_params, body=b_params)
                            if resp and hasattr(resp, 'json'):
                                js_out = resp.json()
                                if isinstance(js_out, dict) and "data" in js_out:
                                    items = js_out["data"]
                                    if isinstance(items, list) and len(items) > 0:
                                        live_val = float(items[0].get("ltp") or items[0].get("lastTradedPrice") or 0)
                                    elif isinstance(items, dict):
                                        live_val = float(items.get("ltp") or items.get("lastTradedPrice") or 0)
                        except:
                            pass

                    # Layer 5: Fallback absolute security shield -> Buy Entry Price
                    if live_val <= 0:
                        live_val = b["prc"]

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
    print(f"\n {unreal_str} 🔸 🏃‍♂️ 🔸 🏃‍♂️ 🥅  {color}{real_str}{Style.RESET_ALL} 🥅\n") 

if __name__ == "__main__": 
    client = get_session() 
    process_lilo_orders(client)

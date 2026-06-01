# _ltp.py
from runltpspxy import get_mid_price

def get_option_live_ltp(client, token_id, ex_seg, fallback_price=0.0):
    """
    Surgically isolates the 5-Tier Fallback Options Pricing Hierarchy.
    Returns the real-time contract premium price or a secure fallback asset value.
    """
    option_live_ltp = 0.0

    # Layer 1: Local Mid Price module algorithm
    try:
        option_live_ltp = get_mid_price(client, token_id, ex_seg)
        if option_live_ltp > 0: return option_live_ltp
    except:
        pass
    
    # Layer 2: Official V2 Client Quotes Array mapping
    try:
        t_payload = [{"instrument_token": str(token_id), "exchange_segment": str(ex_seg)}]
        v2_q = client.quotes(instrument_tokens=t_payload, quote_type="ltp")
        if isinstance(v2_q, dict):
            data_chunk = v2_q.get("data") or v2_q.get("message") or v2_q
            if isinstance(data_chunk, list) and len(data_chunk) > 0:
                option_live_ltp = float(data_chunk[0].get("ltp") or data_chunk[0].get("lastTradedPrice") or 0)
            elif isinstance(data_chunk, dict):
                option_live_ltp = float(data_chunk.get("ltp") or data_chunk.get("lastTradedPrice") or 0)
        elif isinstance(v2_q, list) and len(v2_q) > 0:
            option_live_ltp = float(v2_q[0].get("ltp") or v2_q[0].get("lastTradedPrice") or 0)
        
        if option_live_ltp > 0: return option_live_ltp
    except:
        pass

    # Layer 3: Master Scrip Search data block query
    try:
        scr_res = client.search_scrip(exchangeSegment=ex_seg, instrumentToken=str(token_id))
        if isinstance(scr_res, list) and len(scr_res) > 0:
            option_live_ltp = float(scr_res[0].get("ltp") or scr_res[0].get("lastPrice") or 0)
        elif isinstance(scr_res, dict):
            option_live_ltp = float(scr_res.get("ltp") or scr_res.get("lastPrice") or 0)
        
        if option_live_ltp > 0: return option_live_ltp
    except:
        pass

    # Layer 4: Direct REST client HTTP backend backdoor 
    if hasattr(client, 'rest_client'):
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
                        option_live_ltp = float(items[0].get("ltp") or items[0].get("lastTradedPrice") or 0)
                    elif isinstance(items, dict):
                        option_live_ltp = float(items.get("ltp") or items.get("lastTradedPrice") or 0)
            
            if option_live_ltp > 0: return option_live_ltp
        except:
            pass

    # Layer 5: Fallback absolute security shield -> Entry Cost Baseline
    return fallback_price if fallback_price > 0 else 0.0

#runlilopxy.py
import os 
import json 
import math
import pandas as pd 
from datetime import datetime 
from runclntpxy import get_session 
from runltpspxy import get_mid_price 
from syscnfgpxy import (
    RUNLILOPXY_DEFAULT_FILTER_TIME as DEFAULT_FILTER_TIME,
    SYSCNFGPXY_TIMEZONE,
)
from sysmodepxy import dispatch_mode

# 🔍 STRATEGIC FOOTPRINT: Resolved relative to run/ directory pathing
SQUAREOFF_LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../web/websqrpxy.json"))
def resolve_dynamic_filter_time():
    """Reads risk engine cache to fetch post-reset fresh start time if triggered today."""
    try:
        now_ist = datetime.now(SYSCNFGPXY_TIMEZONE)
        today_str = now_ist.strftime("%Y-%m-%d")
        
        if os.path.exists(SQUAREOFF_LOG_FILE):
            file_mod_timestamp = os.path.getmtime(SQUAREOFF_LOG_FILE)
            file_mod_date_str = datetime.fromtimestamp(
                file_mod_timestamp, SYSCNFGPXY_TIMEZONE
            ).strftime("%Y-%m-%d")
            
            if file_mod_date_str == today_str:
                with open(SQUAREOFF_LOG_FILE, "r") as f:
                    content = f.read().strip()
                    if content:
                        log_data = json.loads(content)
                        
                        # 🎯 THE DESIGN SOLVER: If it's a list, look at the first element. If empty list, fallback to empty dict.
                        if isinstance(log_data, list):
                            log_data = log_data[0] if len(log_data) > 0 else {}
                        
                        # If it's not a dict at this point (or is empty), .get() safely handles it or returns None
                        if isinstance(log_data, dict):
                            if log_data.get("status") == "SUCCESSFUL_SQUARE_OFF_CONFIRMED" and log_data.get("date") == today_str:
                                fresh_start_time = log_data.get("successful_time")
                                if fresh_start_time:
                                    print(f"🔄 Reset detected! Fresh start: {fresh_start_time}")
                                    return fresh_start_time
                                    
        return DEFAULT_FILTER_TIME
    except Exception as e:
        print(f"⚠ Error resolving dynamic time parameters, falling back to default: {e}")
        return DEFAULT_FILTER_TIME

# ⏱️ SURGICAL TIMELINE FILTER INITIALIZATION
FILTER_TIME = resolve_dynamic_filter_time()

def dump_to_json(closed_df): 
    """Writes closed trade realizations to webpnlpxy.json."""
    try: 
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../web/webpnlpxy.json"))
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

def dump_livpos_to_json(open_positions): 
    """Writes active positions metrics to webpospxy.json."""
    try: 
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../web/webpospxy.json"))
        os.makedirs(os.path.dirname(file_path), exist_ok=True) 
        
        livpos_data = [{
            "SYMBOL": str(p["Symbol"]), 
            "QTY": float(p["Qty"]), 
            "PNL": float(p["PNL"])
        } for p in open_positions]
        
        with open(file_path, "w") as f: 
            json.dump(livpos_data, f, indent=4) 
    except Exception as e: 
        print(f"Error dumping livpos to JSON: {e}") 

def _fetch_live_price(client, token_id, ex_seg):
    """5-tier fallback pricing hierarchy. Returns 0.0 when every tier fails."""
    live_val = 0.0

    try:
        live_val = get_mid_price(client, token_id, ex_seg)
    except Exception:
        pass

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
        except Exception:
            pass

    if live_val <= 0:
        try:
            scr_res = client.search_scrip(exchangeSegment=ex_seg, instrumentToken=str(token_id))
            if isinstance(scr_res, list) and len(scr_res) > 0:
                live_val = float(scr_res[0].get("ltp") or scr_res[0].get("lastPrice") or 0)
            elif isinstance(scr_res, dict):
                live_val = float(scr_res.get("ltp") or scr_res.get("lastPrice") or 0)
        except Exception:
            pass

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
        except Exception:
            pass

    return live_val if live_val and live_val > 0 else 0.0


def position_net_quantity(position):
    """Return Kotak's net quantity, including both carry-forward and intraday trades."""
    fields = ("cfBuyQty", "cfSellQty", "flBuyQty", "flSellQty")
    def parse(value):
        quantity = float(str(value or 0).replace(",", "").strip())
        if not math.isfinite(quantity):
            raise ValueError(f"Invalid position quantity: {value}")
        return quantity

    if position.get("net_qty") is not None:
        net_qty = parse(position["net_qty"])
        if net_qty != 0 or not any(position.get(field) is not None for field in fields):
            return net_qty
    if not any(position.get(field) is not None for field in fields):
        raise ValueError("Position row has no recognized quantity fields.")
    return sum(parse(position.get(field, 0)) for field in ("cfBuyQty", "flBuyQty")) - sum(
        parse(position.get(field, 0)) for field in ("cfSellQty", "flSellQty")
    )


def _reconcile_open_with_broker(client, open_positions, strict=False):
    """Trims the tag-matched open lots to what the broker really holds, BEFORE the risk ledger sees them.
    A lot closed outside tag matching (manual sell, untagged square-off) would otherwise stay 'open':
    it would be marked at live price, inflate open_rows (tighter trailing stop) and drift game P&L.
    Symbols with net <= 0 are dropped; when the broker holds less than the open lots add up to,
    the newest lots are kept. If broker positions are unavailable the lots are returned unchanged."""
    if not open_positions:
        return open_positions
    try:
        res = client.positions()
    except Exception as e:
        if strict:
            raise RuntimeError(f"Broker positions call failed during reconciliation: {e}") from e
        print(f"⚠️ Ledger reconcile skipped (positions call failed: {e}).")
        return open_positions

    if (
        not isinstance(res, dict)
        or str(res.get("stat", "")).strip().lower() != "ok"
        or str(res.get("stCode", "")).strip() != "200"
        or not isinstance(res.get("data"), list)
    ):
        if strict:
            raise RuntimeError(f"Invalid Kotak positions response during reconciliation: {res!r}")
        print("⚠️ Ledger reconcile skipped (broker positions unavailable this cycle).")
        return open_positions

    net = {}
    for pos in res["data"]:
        sym = str(pos.get("trdSym", "")).strip()
        try:
            quantity = position_net_quantity(pos)
        except (TypeError, ValueError):
            if strict:
                raise
            print(f"⚠️ Ledger reconcile skipped (invalid quantity for {sym or 'unknown symbol'}).")
            return open_positions
        net[sym] = net.get(sym, 0.0) + quantity

    by_symbol = {}
    for p in open_positions:
        by_symbol.setdefault(p["Symbol"], []).append(p)

    kept = []
    for sym, lots in by_symbol.items():
        remaining = net.get(str(sym).strip(), 0.0)
        if remaining <= 0:
            print(f"🧾 Ledger reconcile: {sym} not held at broker; {len(lots)} stale open lot(s) dropped.")
            continue
        try:
            ordered = sorted(lots, key=lambda x: x["Buy_Time"], reverse=True)   # newest first
        except Exception:
            ordered = list(reversed(lots))
        for lot in ordered:
            if remaining <= 0:
                break
            q = min(float(lot["Qty"]), remaining)
            fixed = dict(lot)
            fixed["Qty"] = q
            fixed["PNL"] = int((fixed["Sell_Prc"] - fixed["Buy_Prc"]) * q)
            kept.append(fixed)
            remaining -= q
    return kept


def _is_no_data_order_report_response(response):
    return (
        isinstance(response, dict)
        and str(response.get("stat", "")).strip().lower() in {"not_ok", "not ok"}
        and str(response.get("stCode", "")).strip() == "5203"
        and str(response.get("errMsg", "")).strip().lower() == "no data"
    )


def _process_lilo_orders_production(client, strict=False, risk_exit_signal=None):
    try: 
        # MASTER RISK LEDGER hook 1: once-a-day stale web-cache override (runs before any data guard)
        try:
            import runexacpxy
            runexacpxy.daily_purge_check()
        except Exception as _risk_err:
            print(f"⚠️ Master risk ledger (daily purge) error: {_risk_err}")

        if not client: 
            _print_summary(0, 0) 
            return pd.DataFrame(), pd.DataFrame() 
        res = client.order_report()
        if _is_no_data_order_report_response(res):
            print("ℹ️ Kotak order report has no data; LILO has nothing to process.")
            _print_summary(0, 0)
            return pd.DataFrame(), pd.DataFrame()
        if (
            not isinstance(res, dict)
            or str(res.get("stat", "")).strip().lower() != "ok"
            or str(res.get("stCode", "")).strip() != "200"
            or not isinstance(res.get("data"), list)
        ):
            if strict:
                raise RuntimeError(f"Invalid Kotak order report response: {res!r}")
            print(f"⚠️ Invalid Kotak order report response: {res!r}")
            _print_summary(0, 0) 
            return pd.DataFrame(), pd.DataFrame() 
            
        df = pd.DataFrame(res["data"])
        if df.empty:
            print("ℹ️ No order rows returned; LILO has nothing to process.")
            _print_summary(0, 0)
            return pd.DataFrame(), pd.DataFrame()

        if "ordSt" not in df.columns:
            message = "Kotak order report is missing the required 'ordSt' field."
            if strict:
                raise RuntimeError(message)
            print(f"⚠️ {message}")
            _print_summary(0, 0)
            return pd.DataFrame(), pd.DataFrame()

        df = df[df["ordSt"].astype(str).str.lower().isin(["complete", "traded"])].copy()
        if df.empty: 
            print("ℹ️ No completed orders returned; LILO has nothing to process.")
            _print_summary(0, 0) 
            return pd.DataFrame(), pd.DataFrame() 
            
        df["qty"] = pd.to_numeric(df["fldQty"], errors='coerce').fillna(0) 
        df["prc"] = pd.to_numeric(df["avgPrc"], errors='coerce').fillna(0) 
        df["dt"] = pd.to_datetime(df["ordDtTm"]) 

        # TIME FILTER BLOCK: Ignore trades before the specified dynamic time window
        df = df[df["dt"].dt.time >= pd.to_datetime(FILTER_TIME).time()].copy()
        if df.empty: 
            _print_summary(0, 0) 
            return pd.DataFrame(), pd.DataFrame() 

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
            # FIXED: Added correct [0] brackets to .iloc property to fix extraction crashes
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

            # One live-price lookup per symbol (not per lot); every lot of a symbol shares the quote
            symbol_live = None
            for b in buys: 
                if b["qty"] > 0: 
                    if symbol_live is None:
                        symbol_live = _fetch_live_price(client, token_id, ex_seg)
                    live_val = symbol_live if symbol_live > 0 else b["prc"]

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

        open_positions = _reconcile_open_with_broker(client, open_positions, strict=strict)
        open_df = pd.DataFrame(open_positions) 
        closed_df = pd.DataFrame(closed_matches) 

        # MASTER RISK LEDGER hook 2: evaluated before the data is handed to any pipeline.
        # SystemExit (confirmed breach) is deliberately NOT caught; every other error only prints.
        try:
            import runexacpxy
            runexacpxy.execute_master_risk_ledger(
                client, open_df, closed_df, exit_signal=risk_exit_signal
            )
        except Exception as _risk_err:
            print(f"⚠️ Master risk ledger error (ledger still returned): {_risk_err}")

        total_unrealized = int(open_df["PNL"].sum()) if not open_df.empty else 0 
        total_realized = int(closed_df["PNL"].sum()) if not closed_df.empty else 0 
        _print_summary(total_unrealized, total_realized) 
        dump_to_json(closed_df) 
        dump_livpos_to_json(open_positions) 
        return open_df, closed_df 
    except Exception as e:
        if strict:
            raise
        print(f"[TAG MATCH ERROR]: {e}") 
        _print_summary(0, 0) 
        return pd.DataFrame(), pd.DataFrame() 


def process_lilo_orders(client, strict=False, risk_exit_signal=None):
    return dispatch_mode(
        "process_lilo_orders",
        _process_lilo_orders_production,
        client=client,
        strict=strict,
        risk_exit_signal=risk_exit_signal,
        test_kwargs={"timezone": SYSCNFGPXY_TIMEZONE},
    )


def _print_summary(total_unrealized, total_realized): 
    from colorama import Fore, Style, init 
    init(autoreset=True) 
    color = Style.BRIGHT + Fore.GREEN if total_realized >= 0 else Fore.RED 
    unreal_str = f"{int(total_unrealized):+06d}" 
    real_str = f"{int(total_realized):+06d}" 
    print(f"\n     🏃‍♂️ 🔸  {unreal_str}  🔸  🏃‍♂️   🥅  {color}{real_str}{Style.RESET_ALL}  🥅\n") 

if __name__ == "__main__": 
    os.environ["PXY_VIEW_ONLY"] = "1"   # viewing run: must not advance the ledger breach count
    client = get_session()
    process_lilo_orders(client)

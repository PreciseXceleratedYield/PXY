# _map.py
import pandas as pd
from colorama import Fore, Style
from _sgnl import _pad_line_to_42

def get_active_strategy_ledger(client):
    """
    Scans broker order logs, nets out volumes by option symbol to handle 
    manual exits, matches automated tracking tags, and returns a clean 
    Pandas DataFrame containing only live, unmatched strategy positions.
    """
    try:
        order_res = client.order_report()  
        orders = order_res.get("data", []) if isinstance(order_res, dict) else order_res
        if not isinstance(orders, list):
            return pd.DataFrame()

        # STAGE 1: SYMBOL QUANTITY VOLUME NETTING (Catches Manual App Exits)
        symbol_net_qty = {}
        for o in orders:
            status = str(o.get("stat", "")).strip().lower()
            if status != "complete": 
                continue
                
            sym = str(o.get("trdSym", "")).strip().upper()
            txn = str(o.get("trnsTp", "")).strip().upper()
            qty = int(float(o.get("fldQty", 0)))
            
            if qty <= 0 or not sym: 
                continue
                
            if sym not in symbol_net_qty:
                symbol_net_qty[sym] = 0
                
            if txn == "B":
                symbol_net_qty[sym] += qty
            elif txn == "S":
                symbol_net_qty[sym] -= qty

        # STAGE 2: PARSING AUTOMATED REVERSAL TAG MODULES
        raw_entries = {}
        closed_tags = set()

        # Step 2A: Collect entry tags closed via standard automated '_X' suffixes
        for o in orders:
            status = str(o.get("stat", "")).strip().lower()
            if status != "complete": 
                continue
            tag = str(o.get("tag") or o.get("ordModNo") or "").strip().upper()
            if tag.endswith("_X"):
                parent_tag = tag[:-2]
                closed_tags.add(parent_tag)

        # Step 2B: Compile active strategy entry nodes, dropping closed ones
        for o in orders:
            status = str(o.get("stat", "")).strip().lower()
            if status != "complete": 
                continue
            tag = str(o.get("tag") or o.get("ordModNo") or "").strip().upper()
            sym = str(o.get("trdSym", "")).strip().upper()
            
            if not (tag.endswith("_B") or tag.endswith("_S")): 
                continue

            qty = int(float(o.get("fldQty", 0)))
            if qty <= 0: 
                continue

            # If volume netting is 0 OR tag match confirms closed, filter it out completely
            if symbol_net_qty.get(sym, 0) == 0 or tag in closed_tags:
                continue

            raw_entries[tag] = {
                "tag": tag,
                "symbol": sym,
                "txn_type": str(o.get("trnsTp", "")).upper().strip(),
                "entry_price": float(o.get("avgPrc", 0)),
                "qty": qty,
                "token": o.get("tok")  
            }

        # STAGE 3: CONVERT TO DATASTRUCT MATRIX FRAMEWORK
        if not raw_entries:
            return pd.DataFrame()
            
        df = pd.DataFrame(raw_entries.values())
        return df

    except Exception as e:
        print(_pad_line_to_42(f"❌ Mapper Error {str(e)[:20]}", Fore.RED, Style.RESET_ALL))
        return pd.DataFrame()

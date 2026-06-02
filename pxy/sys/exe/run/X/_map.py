# _map.py
import asyncio
import pandas as pd
from colorama import Fore, init, Style
from _sgnl import _pad_line_to_42
from _clnt import get_session

init(autoreset=True)

def get_active_strategy_ledger(client, diagnostic_mode=False):
    """
    Scans broker order logs, nets out volumes by option symbol to handle 
    manual exits, matches automated tracking tags, filters out specific broker
    tags containing 'V1L58', and returns a clean Pandas DataFrame of live trades.
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
        v1l58_ignored_tags = set()

        # Step 2A: Collect entry tags closed via standard automated '_X' suffixes
        for o in orders:
            status = str(o.get("stat", "")).strip().lower()
            if status != "complete": 
                continue
            tag = str(o.get("tag") or o.get("ordModNo") or "").strip().upper()
            
            # Filter out and track any exit tags containing V1L58
            if "V1L58" in tag:
                v1l58_ignored_tags.add(tag)
                continue
                
            if tag.endswith("_X"):
                parent_tag = tag[:-2]
                closed_tags.add(parent_tag)

        # Step 2B: Compile active strategy entry nodes
        for o in orders:
            status = str(o.get("stat", "")).strip().lower()
            if status != "complete": 
                continue
            tag = str(o.get("tag") or o.get("ordModNo") or "").strip().upper()
            sym = str(o.get("trdSym", "")).strip().upper()
            
            # ✅ STRICT FILTER: Drop order immediately if the tag contains V1L58
            if "V1L58" in tag:
                v1l58_ignored_tags.add(tag)
                continue
            
            if not (tag.endswith("_B") or tag.endswith("_S")): 
                continue

            qty = int(float(o.get("fldQty", 0)))
            if qty <= 0: 
                continue

            raw_entries[tag] = {
                "tag": tag,
                "symbol": sym,
                "txn_type": str(o.get("trnsTp", "")).upper().strip(),
                "entry_price": float(o.get("avgPrc", 0)),
                "qty": qty,
                "token": o.get("tok")  
            }

        # PASS 3: Separate entries strictly by structural mapping parameters
        open_trades = []
        closed_trades = []

        for tag, details in raw_entries.items():
            sym = details["symbol"]
            # Netted out via manual exit OR tag matches an explicit closure
            if symbol_net_qty.get(sym, 0) == 0 or tag in closed_tags:
                closed_trades.append(details)
            else:
                open_trades.append(details)

        # --- DIAGNOSTIC PASS (Only triggers when running _map.py directly) ---
        if diagnostic_mode:
            print("\n" + "=" * 50)
            print(f"🚫 EXCLUDED SYSTEM TAGS CONTAINING 'V1L58' ({len(v1l58_ignored_tags)})")
            print("=" * 50)
            for vt in sorted(v1l58_ignored_tags):
                print(f"  ❌ IGNORED -> {vt}")

            print("\n" + "=" * 50)
            print(f"🔒 CLOSED / MATCHED STRATEGY TRADES ({len(closed_trades)})")
            print("=" * 50)
            for ct in sorted(closed_trades, key=lambda x: x['tag']):
                print(f"  ✔️ CLOSED -> {ct['tag']} | {ct['symbol']} @ {ct['entry_price']:.2f}")

            print("\n" + "=" * 50)
            print(f"🔓 UNMATCHED OPEN STRATEGY TRADES ({len(open_trades)})")
            print("=" * 50)
            if not open_trades:
                print(f"  NO ACTIVE UNMATCHED OPEN TRADES PRESENT")
            for ot in sorted(open_trades, key=lambda x: x['tag']):
                print(f"  🔥 ACTIVE -> {ot['tag']} | {ot['symbol']} | Qty: {ot['qty']} @ {ot['entry_price']:.2f}")
            print("=" * 50)

        # Strictly return ONLY the open strategy trades as a clean processing DataFrame
        if not open_trades:
            return pd.DataFrame()
            
        return pd.DataFrame(open_trades)

    except Exception as e:
        print(_pad_line_to_42(f"❌ Mapper Error {str(e)[:20]}", Fore.RED, Style.RESET_ALL))
        return pd.DataFrame()

async def main():
    print(f"{Fore.YELLOW}⏳ Connecting to broker session for diagnostics...")
    client = get_session()
    if not client: 
        print("❌ Connection failed.")
        return
    get_active_strategy_ledger(client, diagnostic_mode=True)

if __name__ == "__main__":
    asyncio.run(main())


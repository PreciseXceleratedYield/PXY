# _ord.py
import asyncio
from colorama import Fore, init, Style
from _clnt import get_session

init(autoreset=True)

async def main():
    print(f"{Fore.YELLOW}⏳ Connecting to broker session...")
    client = get_session()
    if not client: 
        print(f"{Fore.RED}❌ Connection failed.")
        return

    try:
        print(f"{Fore.CYAN}📥 Fetching and filtering trade matrix maps...")
        order_res = client.order_report()
        orders = order_res.get("data", []) if isinstance(order_res, dict) else order_res

        if not isinstance(orders, list): 
            print(f"{Fore.RED}❌ Invalid broker response structure.")
            return

        raw_entries = {}
        closed_tags = set()

        # PASS 1: Identify and isolate ALL entry tags closed with an associated '_X' tag (Case-Insensitive)
        for o in orders:
            status = str(o.get("stat", "")).strip().lower()
            if status != "complete": 
                continue
                
            tag = str(o.get("tag") or o.get("ordModNo") or "").strip().upper()
            if tag.endswith("_X"):
                parent_tag = tag[:-2]  # Strips away '_X' to extract the original entry timestamp
                closed_tags.add(parent_tag)

        # PASS 2: Collect valid entry formats matching exactly your timestamp codes (*_B or *_S)
        for o in orders:
            status = str(o.get("stat", "")).strip().lower()
            if status != "complete": 
                continue
                
            tag = str(o.get("tag") or o.get("ordModNo") or "").strip().upper()
            
            # Match exactly the '_B' and '_S' tag signatures found in your raw terminal history logs
            if not (tag.endswith("_B") or tag.endswith("_S")): 
                continue

            qty = int(float(o.get("fldQty", 0)))
            if qty <= 0: 
                continue

            raw_entries[tag] = {
                "symbol": o.get("trdSym", ""),
                "txn_type": str(o.get("trnsTp", "")).upper().strip(),
                "entry_price": float(o.get("avgPrc", 0)),
                "qty": qty,
                "tag": tag
            }

        # PASS 3: Separate entries into Closed vs Open tracking buckets
        open_trades = []
        closed_trades = []

        for tag, details in raw_entries.items():
            if tag in closed_tags:
                closed_trades.append(details)
            else:
                open_trades.append(details)

        # =====================================================================
        # DISPLAY BUCKETS RENDERING PASS
        # =====================================================================
        print("\n" + "=" * 50)
        print(f"🔒 CLOSED / MATCHED STRATEGY TRADES ({len(closed_trades)})")
        print("=" * 50)
        for ct in sorted(closed_trades, key=lambda x: x['tag']):
            print(f"  ✔️ CLOSED -> {ct['tag']} | {ct['symbol']} @ {ct['entry_price']:.2f}")

        print("\n" + "=" * 50)
        print(f"🔓 UNMATCHED OPEN STRATEGY TRADES ({len(open_trades)})")
        print("=" * 50)
        if not open_trades:
            print(f"{Fore.WHITE}  NO ACTIVE UNMATCHED OPEN TRADES PRESENT")
        for ot in sorted(open_trades, key=lambda x: x['tag']):
            print(f"  🔥 ACTIVE -> {ot['tag']} | {ot['symbol']} | Qty: {ot['qty']} @ {ot['entry_price']:.2f}")
        print("=" * 50)

    except Exception as e:
        print(f"{Fore.RED}❌ Diagnostic matrix tracking error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())


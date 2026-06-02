# get_orders.py
import asyncio
from colorama import Fore, init, Style
from _clnt import get_session

init(autoreset=True)

async def main():
    print(f"{Fore.YELLOW}⏳ Connecting to broker session...")
    client = get_session()
    if not client:
        print(f"{Fore.RED}❌ Connection Failed: Could not get a valid session.")
        return

    print(f"{Fore.CYAN}📥 Requesting raw order book data...")
    try:
        order_res = client.order_report()
        
        # Extract the list from the broker's response wrapper
        orders = order_res.get("data", []) if isinstance(order_res, dict) else order_res

        print("=" * 60)
        print(f"📊 TOTAL RAW ORDERS FOUND TODAY: {len(orders) if isinstance(orders, list) else 0}")
        print("=" * 60)

        if not isinstance(orders, list):
            print(f"{Fore.RED}Unexpected structural response format: {order_res}")
            return

        if not orders:
            print("No orders recorded on this account for today yet.")
            return

        # Print every single order sequentially
        for idx, o in enumerate(orders):
            txn = str(o.get("trnsTp", "?")).upper().strip()   # "B" or "S"
            sym = o.get("trdSym", "UNKNOWN")                  # Trading Symbol
            qty = o.get("fldQty", 0)                          # Filled Quantity
            stat = o.get("stat", "UNKNOWN")                   # Order Status (COMPLETE, REJECTED, etc)
            tag = o.get("tag") or o.get("ordModNo") or "NONE" # Custom Tag or Reference ID
            price = o.get("avgPrc", 0)                        # Execution Price
            
            print(f"[{idx:02d}] {txn} | {sym} | Qty: {qty} | Price: {price} | Status: {stat} | Tag: {tag}")
            
        print("=" * 60)

    except Exception as e:
        print(f"{Fore.RED}❌ Critical error reading order book: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())

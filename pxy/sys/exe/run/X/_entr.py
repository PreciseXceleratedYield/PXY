# _test_ledger.py
import asyncio
from _clnt import get_session
from _exit import analyze_and_map_all_orders

async def test():
    client = get_session()
    if not client:
        print("❌ Cannot connect to broker session.")
        return
        
    print("⏳ Scanning broker order book history...")
    open_trades, closed_trades = analyze_and_map_all_orders(client)
    
    print("\n==========================================")
    print(f"📊 HISTORICAL CLOSED TAGS FOUND: {len(closed_trades)}")
    print("==========================================")
    for ct in closed_trades:
        print(f"  ✔️ CLOSED: {ct['tag']} | Symbol: {ct['symbol']} | Qty: {ct['qty']}")
        
    print("\n==========================================")
    print(f"🔓 UNMATCHED OPEN TAGS FOUND: {len(open_trades)}")
    print("==========================================")
    for ot in open_trades:
        print(f"  🔥 ACTIVE: {ot['tag']} | Symbol: {ot['symbol']} | Qty: {ot['qty']}")

if __name__ == "__main__":
    asyncio.run(test())

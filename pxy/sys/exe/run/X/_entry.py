# _entry.py
import sys
import asyncio
import os
import re
import time
from datetime import datetime, date, timedelta, time as dt_time
import pytz
from colorama import Fore, init, Style

# =====================================================================
# 1. FLAT INTEGRATED GLOBAL CONFIGURATION (STRICT RISK CAP)
# =====================================================================
TICKER = "^NSEI"  # Strictly tracking NIFTY 50 Index
LOT_SIZE = 65     # Standard NIFTY Lot size
MAX_QTY = 65      # HARD RISK LIMIT: Max allowed execution quantity per order
DEBUG = False 

HOLIDAYS = [
    "26-Jan-2026", "06-Mar-2026", "20-Mar-2026", "31-Mar-2026",
    "03-Apr-2026", "14-Apr-2026", "01-May-2026", "15-Aug-2026",
    "02-Oct-2026", "21-Oct-2026", "06-Nov-2026", "24-Nov-2026", "25-Dec-2026"
]
HOLIDAYS = [datetime.strptime(h, "%d-%b-%Y").date() for h in HOLIDAYS]

init(autoreset=True)

# =====================================================================
# 2. INTEGRATED NIFTY SYMBOL GENERATOR
# =====================================================================
def get_target_tuesday():
    today = date.today()
    days_until_tue = (1 - today.weekday() + 7) % 7
    if today.weekday() <= 1:
        days_until_tue += 7
    target_tue = today + timedelta(days=days_until_tue)
    while target_tue in HOLIDAYS:
        target_tue -= timedelta(days=1)
    return target_tue

def is_monthly_expiry(expiry_date):
    return (expiry_date + timedelta(days=7)).month != expiry_date.month

def get_nifty_symbol(strike):
    try:
        if not strike or strike == 0:
            return "NA"
        opt_type = "CE"
        expiry = get_target_tuesday()
        yy = str(expiry.year)[-2:]

        if is_monthly_expiry(expiry):
            mm_str = expiry.strftime('%b').upper()
            return f"NIFTY{yy}{mm_str}{int(strike)}{opt_type}"
        else:
            month_map = {10: "O", 11: "N", 12: "D"}
            mm_char = month_map.get(expiry.month, str(expiry.month))
            dd_str = f"{expiry.day:02d}"
            return f"NIFTY{yy}{mm_char}{dd_str}{int(strike)}{opt_type}"
    except Exception as e:
        print(f"❌ Symbol Generation Error: {e}")
        return "NA"

# =====================================================================
# 3. GLOBAL POSITION RATIO ENGINE
# =====================================================================
def get_global_position_summary(client):
    global_long_lots = 0
    global_short_lots = 0
    try:
        pos_res = client.positions()
        positions = pos_res.get("data", [])
        if not isinstance(positions, list):
            return {"long": 0, "short": 0}

        for pos in positions:
            net_qty = float(pos.get("net_qty", 0))
            if net_qty == 0:
                buy = float(pos.get("flBuyQty", 0))
                sell = float(pos.get("flSellQty", 0))
                net_qty = buy - sell

            if abs(net_qty) > 0:
                symbol = str(pos.get("trdSym", "")).upper()
                if not symbol.endswith("CE") or "NIFTY" not in symbol or "BANKNIFTY" in symbol:
                    continue
                current_lots = int(abs(net_qty) / LOT_SIZE)
                if net_qty > 0:
                    global_long_lots += current_lots
                elif net_qty < 0:
                    global_short_lots += current_lots
    except Exception as e:
        print(f"❌ Global Position Engine Error: {e}")
        return {"long": 0, "short": 0}
    return {"long": global_long_lots, "short": global_short_lots}

# =====================================================================
# 4. ORDER ROUTING INTERFACE
# =====================================================================
def execute_order(client, symbol, qty, txn_type):
    try:
        if int(qty) > MAX_QTY:
            print(f"{Fore.RED}⚠️ WARNING: Enforcing MAX_QTY cap ceiling of {MAX_QTY}.")
            qty = MAX_QTY
        order_tag = datetime.now(pytz.timezone("Asia/Kolkata")).strftime('%H%M%S')
        params = {
            "exchange_segment": "nse_fo",
            "product": "NRML",
            "price": "0",
            "order_type": "MKT",
            "quantity": str(qty),
            "validity": "DAY",
            "trading_symbol": symbol,
            "transaction_type": txn_type,
            "amo": "NO",
            "tag": order_tag  
        }
        res = client.place_order(**params)
        print(f"{Fore.CYAN}🚀 ORDER PLACED | SYMBOL: {symbol} | TYPE: {txn_type} | QTY: {qty} | TAG: {order_tag}")
        return {"stat": "OK" if res and str(res).strip() else "FAIL"}
    except Exception as e:
        return {"stat": "FAIL", "err": str(e)}

# =====================================================================
# 5. CORE EXECUTION ENGINE LOOP
# =====================================================================
async def main():
    try:
        # 1. Market Timing Validation Check
        IST = pytz.timezone("Asia/Kolkata")
        now = datetime.now(IST).time()
        if (dt_time(9, 14) <= now < dt_time(9, 16)) or (dt_time(15, 19) <= now < dt_time(15, 31)):
            print(f"{Fore.YELLOW}⏳ Market buffer timing restriction block active.")
            return

        # 2. Safe Flat Directory Imports (FIXED MATCH NAME TO _sgnl.py)
        from _sgnl import get_all_data
        from _clnt import get_session
        
        # 3. Pull Live Strategy Streams
        data = get_all_data()
        entry_signal = str(data.get("entry", "")).upper().strip()
        ltp = float(data.get("price", 0))
        if ltp == 0 or not entry_signal: return

        # 4. Strict Exact Signal Filter Matches
        if entry_signal == "BUY":
            sig = "BUY"
        elif entry_signal == "SELL":
            sig = "SELL"
        else:
            return

        # 5. Connect and Pull Client Object
        client = get_session()
        if not client: return

        # 6. Assess Global Account Ratios
        ce_positions = get_global_position_summary(client)
        global_longs = ce_positions["long"]
        global_shorts = ce_positions["short"]
        
        symbol, res = None, {"stat": "SKIPPED"}
        
        # 6b. VERY STRICT 65:65 MAX RISK CAP GUARDRAIL
        if global_longs >= 1 and global_shorts >= 1:
            print(f"{Fore.RED}🛑 STRICT CEILING ENGAGED (65 Long : 65 Short). Entry loops LOCKED down.")
            return

        # 7. Execute Controlled Order Entry Decisions
        if sig == "BUY":
            if global_longs < global_shorts or (global_longs == 0 and global_shorts == 0):
                qty_needed = LOT_SIZE 
                target_strike = round(ltp / 100) * 100
                symbol = get_nifty_symbol(target_strike)
                res = execute_order(client, symbol, qty_needed, "B")

        elif sig == "SELL":
            # FIXED: Stripped out broken syntax row to ensure uniform global_shorts logic
            if global_shorts < global_longs or (global_longs == 0 and global_shorts == 0):
                qty_needed = LOT_SIZE
                base_100 = round(ltp / 100) * 100
                target_strike = base_100 - 50 if abs(ltp - (base_100 - 50)) < abs(ltp - (base_100 + 50)) else base_100 + 50
                symbol = get_nifty_symbol(target_strike)
                res = execute_order(client, symbol, qty_needed, "S")

        print(f"📦 Account Ratios -> Longs: {global_longs} Lots | Shorts: {global_shorts} Lots | Status: {res.get('stat')}")
        
    except Exception as e:
        print(f"❌ Core Execution Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())


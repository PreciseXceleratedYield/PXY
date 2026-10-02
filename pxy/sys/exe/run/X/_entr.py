import sys
import os
import json
import asyncio
from datetime import datetime, date, timedelta, time as dt_time
import pytz
from colorama import Fore, init, Style
from _sgnl import _pad_line_to_42  

TICKER = "^NSEI"  
LOT_SIZE = 65     
MAX_QTY = 65      
STATE_FILE = "trades.json"

HOLIDAYS = [
    "26-Jan-2026", "06-Mar-2026", "20-Mar-2026", "31-Mar-2026",
    "03-Apr-2026", "14-Apr-2026", "01-May-2026", "15-Aug-2026",
    "02-Oct-2026", "21-Oct-2026", "06-Nov-2026", "24-Nov-2026", "25-Dec-2026"
]
HOLIDAYS = [datetime.strptime(h, "%d-%b-%Y").date() for h in HOLIDAYS]

init(autoreset=True)

def load_trades():
    if not os.path.exists(STATE_FILE): return {}
    try:
        with open(STATE_FILE, "r") as f: return json.load(f)
    except: return {}

def broadcast_signal_to_ledger(current_signal):
    """ Broadcasts active trend signals into json for _exit.py rule mapping """
    try:
        trades = load_trades()
        updated = False
        for tag in trades:
            if trades[tag].get("status") == "OPEN":
                trades[tag]["current_signal"] = str(current_signal).upper().strip()
                updated = True
        if updated:
            with open(STATE_FILE, "w") as f:
                json.dump(trades, f, indent=4)
    except Exception as e:
        print(f"⚠️ Signal Sync Error: {str(e)[:20]}")

def get_target_tuesday():
    today = date.today()
    days_until_tue = (1 - today.weekday() + 7) % 7
    if today.weekday() <= 1: days_until_tue += 7
    target_tue = today + timedelta(days=days_until_tue)
    while target_tue in HOLIDAYS: target_tue -= timedelta(days=1)
    return target_tue

def get_nifty_symbol(strike):
    try:
        if not strike or strike == 0: return "NA"
        opt_type = "CE"
        expiry = get_target_tuesday()
        yy = str(expiry.year)[-2:]
        if (expiry + timedelta(days=7)).month != expiry.month:
            return f"NIFTY{yy}{expiry.strftime('%b').upper()}{int(strike)}{opt_type}"
        else:
            m_map = {10: "O", 11: "N", 12: "D"}
            return f"NIFTY{yy}{m_map.get(expiry.month, str(expiry.month))}{expiry.day:02d}{int(strike)}{opt_type}"
    except: return "NA"

def get_global_position_summary(client):
    gl, gs = 0, 0
    try:
        pos_res = client.positions()
        positions = pos_res.get("data", [])
        if not isinstance(positions, list): return {"long": 0, "short": 0}
        for pos in positions:
            net_qty = float(pos.get("net_qty", 0))
            if net_qty == 0: net_qty = float(pos.get("flBuyQty", 0)) - float(pos.get("flSellQty", 0))
            if abs(net_qty) > 0:
                symbol = str(pos.get("trdSym", "")).upper()
                if not symbol.startswith("NIFTY") or not symbol.endswith("CE"): continue
                if net_qty > 0: gl += int(abs(net_qty) / LOT_SIZE)
                elif net_qty < 0: gs += int(abs(net_qty) / LOT_SIZE)
    except: pass
    return {"long": gl, "short": gs}

def execute_order(client, symbol, qty, txn_type):
    try:
        base_tag = datetime.now(pytz.timezone("Asia/Kolkata")).strftime('%m%d%H%M%S')
        order_tag = f"{base_tag}_ENTRY"
        
        params = {
            "exchange_segment": "nse_fo", "product": "NRML", "price": "0",
            "order_type": "MKT", "quantity": str(qty), "validity": "DAY",
            "trading_symbol": symbol, "transaction_type": txn_type, "amo": "NO", "tag": order_tag  
        }
        res = client.place_order(**params)
        if res and str(res).strip():
            out_str = f"🚀 ROUTED ENTRY|{symbol}|{txn_type}|TAG:{order_tag}"
            print(_pad_line_to_42(out_str, "\033[96m", "\033[0m"))
        return {"stat": "OK" if res and str(res).strip() else "FAIL"}
    except Exception as e:
        return {"stat": "FAIL", "err": str(e)}

async def trade_cycle():
    IST = pytz.timezone("Asia/Kolkata")
    now = datetime.now(IST).time()
    if (dt_time(9, 14) <= now < dt_time(9, 16)) or (dt_time(15, 19) <= now < dt_time(15, 31)): return

    from _sgnl import get_all_data
    from _clnt import get_session
    
    data = get_all_data()
    entry_signal = str(data.get("entry", "")).upper().strip()
    ltp = float(data.get("price", 0))
    if ltp == 0 or entry_signal not in ["BUY", "BULL", "SELL", "BEAR"]: return
   
    client = get_session()
    if not client: return
    
    summary = get_global_position_summary(client)
    global_longs, global_shorts = summary["long"], summary["short"]

    current_buy_qty = global_longs * LOT_SIZE
    current_sell_qty = global_shorts * LOT_SIZE

    # Normalise strategy indicators
    normalized_signal = "BUY" if entry_signal in ["BUY", "BULL"] else "SELL"
    
    # Update active open records with the current signal configuration
    broadcast_signal_to_ledger(normalized_signal)

    # Enforce strict 65 max lot risk restrictions
    if normalized_signal == "BUY" and current_buy_qty >= 65:
        print(_pad_line_to_42("🔒 GLOBAL BLOCK | BUY MAX REACHED (65)", "\033[93m", "\033[0m"))
        return

    if normalized_signal == "SELL" and current_sell_qty >= 65:
        print(_pad_line_to_42("🔒 GLOBAL BLOCK | SELL MIN REACHED (-65)", "\033[93m", "\033[0m"))
        return

    # Trigger entries only if no matching running direction exists
    if normalized_signal == "BUY" and global_longs == 0:
        target_strike = round(ltp / 100) * 100
        symbol = get_nifty_symbol(target_strike)
        execute_order(client, symbol, LOT_SIZE, "B")
    elif normalized_signal == "BUY":
        print(_pad_line_to_42("🔒 HOLD | BULL ACTIVE | NO ADD", "\033[93m", "\033[0m"))

    elif normalized_signal == "SELL" and global_shorts == 0:
        base_100 = round(ltp / 100) * 100
        target_strike = base_100 - 50 if abs(ltp - (base_100 - 50)) < abs(ltp - (base_100 + 50)) else base_100 + 50
        symbol = get_nifty_symbol(target_strike)
        execute_order(client, symbol, LOT_SIZE, "S")
    elif normalized_signal == "SELL":
        print(_pad_line_to_42("🔒 HOLD | BEAR ACTIVE | NO ADD", "\033[93m", "\033[0m"))

async def main():
    try:
        await trade_cycle()
    except Exception as e:
        print(_pad_line_to_42(f"⚠️ Entry Failure: {str(e)[:22]}", "\033[91m", "\033[0m"))

if __name__ == "__main__":
    asyncio.run(main())

# _entr.py
import sys
import asyncio
from datetime import datetime, date, timedelta, time as dt_time
import pytz
from colorama import Fore, init, Style
from _sgnl import _pad_line_to_42  

TICKER = "^NSEI"  
LOT_SIZE = 65     
MAX_QTY = 65      

HOLIDAYS = [
    "26-Jan-2026", "06-Mar-2026", "20-Mar-2026", "31-Mar-2026",
    "03-Apr-2026", "14-Apr-2026", "01-May-2026", "15-Aug-2026",
    "02-Oct-2026", "21-Oct-2026", "06-Nov-2026", "24-Nov-2026", "25-Dec-2026"
]
HOLIDAYS = [datetime.strptime(h, "%d-%b-%Y").date() for h in HOLIDAYS]

init(autoreset=True)

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
                if not symbol.endswith("CE") or "NIFTY" not in symbol or "BANKNIFTY" in symbol: continue
                if net_qty > 0: gl += int(abs(net_qty) / LOT_SIZE)
                elif net_qty < 0: gs += int(abs(net_qty) / LOT_SIZE)
    except: pass
    return {"long": gl, "short": gs}

def execute_order(client, symbol, qty, txn_type):
    try:
        # Formats tag explicitly as MMDDHHMMSS_ENTRY
        base_tag = datetime.now(pytz.timezone("Asia/Kolkata")).strftime('%m%d%H%M%S')
        order_tag = f"{base_tag}_ENTRY"
        
        params = {
            "exchange_segment": "nse_fo", "product": "NRML", "price": "0",
            "order_type": "MKT", "quantity": str(qty), "validity": "DAY",
            "trading_symbol": symbol, "transaction_type": txn_type, "amo": "NO", "tag": order_tag  
        }
        res = client.place_order(**params)
        if res and str(res).strip():
            out_str = f"🚀 ROUTED|{symbol}|{txn_type}|TAG:{order_tag}"
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

    # --- STRICT ONE-LOT MAX QUANTITY PROTECTIONS ---
    if entry_signal in ["BUY", "BULL"] and current_buy_qty >= 65 and global_shorts == 0:
        print(_pad_line_to_42("🔒 GLOBAL BLOCK | BUY MAX REACHED (65)", "\033[93m", "\033[0m"))
        return

    if entry_signal in ["SELL", "BEAR"] and current_sell_qty >= 65 and global_longs == 0:
        print(_pad_line_to_42("🔒 GLOBAL BLOCK | SELL MIN REACHED (-65)", "\033[93m", "\033[0m"))
        return

    if entry_signal in ["BUY", "BULL"]:
        if global_shorts > 0:
            print(_pad_line_to_42("🔄 EXITING BEAR | SQUARING OFF", "\033[95m", "\033[0m"))
            base_100 = round(ltp / 100) * 100
            target_strike = base_100 - 50 if abs(ltp - (base_100 - 50)) < abs(ltp - (base_100 + 50)) else base_100 + 50
            symbol = get_nifty_symbol(target_strike)
            execute_order(client, symbol, LOT_SIZE, "B")
            return

        if global_longs == 0:
            target_strike = round(ltp / 100) * 100
            symbol = get_nifty_symbol(target_strike)
            execute_order(client, symbol, LOT_SIZE, "B")
        else:
            print(_pad_line_to_42("🔒 HOLD | BULL ACTIVE | NO ADD", "\033[93m", "\033[0m"))

    elif entry_signal in ["SELL", "BEAR"]:
        if global_longs > 0:
            print(_pad_line_to_42("🔄 EXITING BULL | SQUARING OFF", "\033[95m", "\033[0m"))
            target_strike = round(ltp / 100) * 100
            symbol = get_nifty_symbol(target_strike)
            execute_order(client, symbol, LOT_SIZE, "S")
            return

        if global_shorts == 0:
            base_100 = round(ltp / 100) * 100
            target_strike = base_100 - 50 if abs(ltp - (base_100 - 50)) < abs(ltp - (base_100 + 50)) else base_100 + 50
            symbol = get_nifty_symbol(target_strike)
            execute_order(client, symbol, LOT_SIZE, "S")
        else:
            print(_pad_line_to_42("🔒 HOLD | BEAR ACTIVE | NO ADD", "\033[93m", "\033[0m"))

async def main():
    try:
        await trade_cycle()
    except Exception as e:
        err_msg = f"⚠️ Entry Failure: {str(e)[:22]}"
        print(_pad_line_to_42(err_msg, "\033[91m", "\033[0m"))

if __name__ == "__main__":
    asyncio.run(main())


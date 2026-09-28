# ==============================================================================
# 🛠️ PART 1 OF 2: UTILITY LAYER (Layout Calculations, Math Padding & Telegram)
# ==============================================================================

import sys
from datetime import datetime

def debug_log(section, msg, data=None):
    """Streams live data structure dumps directly to stderr without breaking text layout."""
    ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    print(f"[DEBUG][{ts}][{section}] {msg}", file=sys.stderr)
    if data is not None:
        print(f"[RAW_PAYLOAD] {repr(data)}\n", file=sys.stderr)

def emoji_len(text):
    """Calculates the true layout width by counting emojis as 2 characters."""
    count = 0
    for char in text:
        if ord(char) > 0xffff or char in "💰⏳📝📊🟢🔴🏆🚀❌":
            count += 2
        else:
            count += 1
    return count

def pad_row(text, width=30):
    """Pads text to the strict visual width, taking emoji size into account."""
    curr_len = emoji_len(text)
    if curr_len >= width:
        sliced = ""
        running_w = 0
        for char in text:
            char_w = 2 if (ord(char) > 0xffff or char in "💰⏳📝📊🟢🔴🏆🚀❌") else 1
            if running_w + char_w <= width:
                sliced += char
                running_w += char_w
            else:
                break
        return sliced
    return text + (" " * (width - curr_len))

def force_trailing_zero(value, context_tag="MATH"):
    """Enforces trailing zero logic and prints input/output changes to log."""
    try:
        if value is None:
            return 0.0
        val_int = int(round(float(value)))
        remainder = val_int % 10
        if remainder >= 5:
            val_int += (10 - remainder)
        else:
            val_int -= remainder
        return float(val_int)
    except (ValueError, TypeError) as e:
        debug_log(f"{context_tag}_ERR", f"Failed conversion on raw value: {value} ({str(e)})")
        return 0.0

def send_telegram_payload(message_text, bot_token, chat_id):
    """Dispatches the formatted layout message to your Telegram channel."""
    if "PLACEHOLDER" in bot_token or "PLACEHOLDER" in chat_id:
        return

    url = f"https://telegram.org{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "Markdown"
    }
    try:
        import urllib.request
        import urllib.parse
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=5) as response:
            pass
    except Exception:
        pass

# ==============================================================================
# 🚀 PART 2 OF 2: CORE ENGINE LAYER (API Fetching, Data Processing & Execution)
# ==============================================================================

#!/usr/bin/env python3
import sys
import pytz
import traceback
from datetime import datetime, time
from runclntpxy import get_session

# ⚙️ CONFIGURATION & ENVIRONMENTAL SETTINGS
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_PLACEHOLDER"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID_PLACEHOLDER"

IST = pytz.timezone("Asia/Kolkata")
W = 30  # Strict 30-character width tracking layout

def run_snapshot_report():
    """Generates ledger snapshot separating open tracking from fully realized positions."""
    now_ist = datetime.now(IST)
    current_time = now_ist.time()
    
    start_market = time(9, 15)
    end_market = time(15, 45)
    
    # 🕒 Strict Time Restriction Gate (9:15 AM to 3:45 PM IST)
    if start_market <= current_time <= end_market:
        print("=" * W)
        print(pad_row("🛰️ PXY MONITOR LIVE ENGINE 🟢", W))
        print("=" * W)
        print(pad_row("You already started the engine", W))
        print(pad_row("based on your configurations", W))
        print(pad_row("and your preferences...", W))
        print(pad_row("Wait for market hour to be", W))
        print(pad_row("completed...", W))
        print("=" * W)
        return

    client = get_session()
    if not client:
        print(pad_row("❌ API Connection Blank", W))
        return

    positions_list = []
    orders_list = []
    raw_margin = 0.0

    try:
        pos_res = client.positions()
        positions_list = pos_res.get("data", []) if isinstance(pos_res, dict) else getattr(pos_res, "data", [])
    except Exception as e:
        debug_log("API_EXCEP_POSITIONS", "Positions extraction broken down.", str(e))
    if positions_list is None:
        positions_list = []

    try:
        try:
            ord_res = client.order_report()
        except AttributeError:
            ord_res = client.orders()
        orders_list = ord_res.get("data", []) if isinstance(ord_res, dict) else getattr(ord_res, "data", [])
    except Exception as e:
        debug_log("API_EXCEP_ORDERS", "Orders extraction broken down.", str(e))
    if orders_list is None:
        orders_list = []

    # Safe Balance Parser Strategy
    margin_res = None
    for method_name in ["balances", "limits", "margin"]:
        try:
            margin_res = getattr(client, method_name)()
            debug_log("API_RESPONSE_MARGIN", f"Raw bounds payload via {method_name}:", margin_res)
            break
        except AttributeError:
            continue
        except Exception:
            continue

    if margin_res is not None:
        # Avoid forcing list[0] slice conversion if the broker returns an explicit root map dictionary
        margin_data = margin_res.get("data", margin_res) if isinstance(margin_res, dict) else getattr(margin_res, "data", margin_res)
        if isinstance(margin_data, list) and len(margin_data) > 0:
            margin_data = margin_data[0]
            
        if isinstance(margin_data, dict):
            # Intercept broad key variations present across Kotak SDK patches
            raw_margin = margin_data.get("availableMargin", 
                         margin_data.get("cfBal", 
                         margin_data.get("netBal", 
                         margin_data.get("grosResLmt", 
                         margin_data.get("marUpdAmt", 0.0)))))
        else:
            raw_margin = getattr(margin_data, "availableMargin", 
                         getattr(margin_data, "cfBal", 
                         getattr(margin_data, "netBal", 
                         getattr(margin_data, "grosResLmt", 
                         getattr(margin_data, "marUpdAmt", 0.0)))))

    output_lines = []
    output_lines.append("=" * W)
    output_lines.append(pad_row(f"🚀 PXY | {now_ist.strftime('%d-%b %H:%M')}", W))
    output_lines.append("=" * W)

    # 1. Available Funds Processing
    sanitized_margin = int(force_trailing_zero(raw_margin, "MARGIN"))
    output_lines.append(pad_row(f"💰 Fnd: ₹{sanitized_margin:,}", W))
    output_lines.append("-" * W)

    # 2. Active Working Orders Processing
    active_orders = []
    for o in orders_list:
        status = o.get("ordSt", o.get("status", "")) if isinstance(o, dict) else getattr(o, "ordSt", getattr(o, "status", ""))
        if str(status).lower() in ["working", "open", "validation pending"]:
            active_orders.append(o)

    output_lines.append(pad_row(f"⏳ Ord Working: {len(active_orders)}", W))
    for ord in active_orders:
        sym = str(ord.get("trdSym", "UNK") if isinstance(ord, dict) else getattr(ord, "trdSym", "UNK"))[-7:]
        side_raw = ord.get("trnsTp", ord.get("side", "")) if isinstance(ord, dict) else getattr(ord, "trnsTp", getattr(ord, "side", ""))
        side = "B" if "B" in str(side_raw).upper() else "S"
        qty = abs(int(float(ord.get("qty", 0) if isinstance(ord, dict) else getattr(ord, "qty", 0))))
        price = int(force_trailing_zero(ord.get("avgPrc", ord.get("prc", 0.0)) if isinstance(ord, dict) else getattr(ord, "avgPrc", getattr(ord, "prc", 0.0)), "ORD_PRICE"))
        output_lines.append(pad_row(f" 📝 {side}|{sym}|Q:{qty}|P:₹{price}", W))
    output_lines.append("-" * W)

    # 3. Open vs Realized Position Processing
    open_positions = []
    closed_positions = []
    total_pnl = 0.0
    
    for pos in positions_list:
        buy_amt = float(pos.get("buyAmt", 0.0))
        sell_amt = float(pos.get("sellAmt", 0.0))
        fl_buy_qty = float(pos.get("flBuyQty", 0.0))
        fl_sell_qty = float(pos.get("flSellQty", 0.0))
        
        net_qty = fl_buy_qty - fl_sell_qty
        pos_pnl = sell_amt - buy_amt
        total_pnl += pos_pnl
        
        if net_qty == 0:
            closed_positions.append((pos, fl_buy_qty, pos_pnl))
        else:
            open_positions.append((pos, net_qty, pos_pnl))
            
    # Print Live Open Rows (if any exist)
    output_lines.append(pad_row(f"📊 Live Open: {len(open_positions)}", W))
    for pos, qty, pnl in open_positions:
        sym = str(pos.get("trdSym", "UNK"))[-7:]
        sanitized_pnl = int(force_trailing_zero(pnl, "OPEN_PNL"))
        status_flag = "🟢" if sanitized_pnl >= 0 else "🔴"
        output_lines.append(pad_row(f" {status_flag} {sym} [Q:{int(qty)}]", W))

    if open_positions:
        output_lines.append("-" * W)

    # Print Realized Rows
    output_lines.append(pad_row(f"🏆 Realized Positions: {len(closed_positions)}", W))
    for pos, qty, pnl in closed_positions:
        sym = str(pos.get("trdSym", "UNK"))[-7:]
        fl_buy_qty = float(pos.get("flBuyQty", 0.0))
        fl_sell_qty = float(pos.get("flSellQty", 0.0))
        
        avg_buy = (float(pos.get("buyAmt", 0.0)) / fl_buy_qty) if fl_buy_qty > 0 else 0.0
        avg_sell = (float(pos.get("sellAmt", 0.0)) / fl_sell_qty) if fl_sell_qty > 0 else 0.0
        
        sanitized_pnl = int(force_trailing_zero(pnl, "CLOSED_PNL"))
        status_flag = "🟢" if sanitized_pnl >= 0 else "🔴"
        
        output_lines.append(pad_row(f" {status_flag} {sym} [Q:{int(qty)}]", W))
        pnl_str = f"₹{sanitized_pnl:,}"
        metrics = f"   B:{int(force_trailing_zero(avg_buy))}|S:{int(force_trailing_zero(avg_sell))}"
        
        space_needed = W - emoji_len(metrics) - emoji_len(pnl_str)
        output_lines.append(f"{metrics}{' ' * space_needed}{pnl_str}" if space_needed > 0 else pad_row(f"{metrics} P:{pnl_str}", W))
        
    output_lines.append("-" * W)
    
    # 4. Total Consolidated PnL Processing
    final_pnl = int(force_trailing_zero(total_pnl, "FINAL_SUM"))
    pnl_val = f"₹{final_pnl:,}"
    sum_space = W - emoji_len("🏆 Net PnL:") - emoji_len(pnl_val)
    output_lines.append(f"🏆 Net PnL:{' ' * max(1, sum_space)}{pnl_val}")
    output_lines.append("=" * W)

    full_message_payload = "\n".join(output_lines)
    print(full_message_payload)
    send_telegram_payload(f"```text\n{full_message_payload}\n```", TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)

if __name__ == "__main__":
    run_snapshot_report()

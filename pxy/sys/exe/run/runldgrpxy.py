# ==============================================================================
# 🛠️ PART 1: UTILITY LAYER (Layout Calculations, Math Formatting & Padding)
# ==============================================================================

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

def force_trailing_zero(value):
    """Enforces the strict rule that the final digit of the integer part must be 0."""
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
    except (ValueError, TypeError):
        return 0.0

def send_telegram_payload(message_text):
    """Dispatches the formatted layout message to your Telegram channel."""
    if "PLACEHOLDER" in TELEGRAM_BOT_TOKEN or "PLACEHOLDER" in TELEGRAM_CHAT_ID:
        return

    url = f"https://telegram.org{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_text,
        "parse_mode": "Markdown"
    }
    try:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=5) as response:
            pass
    except Exception:
        pass

# ==============================================================================
# 🚀 PART 2: CORE ENGINE LAYER (API Fetching, Data Processing & Output Generation)
# ==============================================================================

#!/usr/bin/env python3
"""
PXY® Trading System - Ledger Snapshot Engine (exeldgrpxy.py)
Protected by international copyright laws. All rights reserved globally by PXY® and PreciseXceleratedYield Pvt Ltd™.

Purpose: Single-run snapshot formatted strictly to a 30-character maximum row width.
         Connects via runclntpxy.get_session() matching your working script connections.
Design Rule: Guarantees that the last digit of calculated integer numbers ends in 0.
"""

import sys
import urllib.request
import urllib.parse
import pytz
from datetime import datetime, time
from runclntpxy import get_session

# ⚙️ CONFIGURATION & ENVIRONMENTAL SETTINGS
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_PLACEHOLDER"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID_PLACEHOLDER"

IST = pytz.timezone("Asia/Kolkata")
W = 30  # Strict 30-character width tracking layout

def run_snapshot_report():
    """Generates the mobile telemetry report via Kotak Neo V2 API sessions."""
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

    try:
        # 1. Fetch Positions Safely
        pos_res = client.positions()
        positions_list = pos_res.get("data", []) if isinstance(pos_res, dict) else getattr(pos_res, "data", [])
        if positions_list is None:
            positions_list = []
        
        # 2. Fetch Orders Safely
        try:
            ord_res = client.order_report()
            orders_list = ord_res.get("data", []) if isinstance(ord_res, dict) else getattr(ord_res, "data", [])
        except AttributeError:
            ord_res = client.orders()
            orders_list = ord_res.get("data", []) if isinstance(ord_res, dict) else getattr(ord_res, "data", [])
        if orders_list is None:
            orders_list = []

        # 3. Fetch Limits/Balances Safely
        try:
            margin_res = client.balances()
        except AttributeError:
            try:
                margin_res = client.limits()
            except AttributeError:
                margin_res = client.margin()

        margin_data = margin_res.get("data", margin_res) if isinstance(margin_res, dict) else getattr(margin_res, "data", margin_res)
        if isinstance(margin_data, list) and len(margin_data) > 0:
            margin_data = margin_data
            
        if isinstance(margin_data, dict):
            raw_margin = margin_data.get("availableMargin", margin_data.get("cfBal", 0.0))
        else:
            raw_margin = getattr(margin_data, "availableMargin", getattr(margin_data, "cfBal", 0.0))

    except Exception as e:
        print(pad_row(f"❌ API Failure: {str(e)}", W))
        return

    output_lines = []
    output_lines.append("=" * W)
    output_lines.append(pad_row(f"🚀 PXY | {now_ist.strftime('%d-%b %H:%M')}", W))
    output_lines.append("=" * W)
    output_lines.append(pad_row("Here is the results based on", W))
    output_lines.append(pad_row("your instructions and config", W))
    output_lines.append(pad_row("you ran:", W))
    output_lines.append("=" * W)

    # 1. Available Funds Processing
    sanitized_margin = int(force_trailing_zero(raw_margin))
    output_lines.append(pad_row(f"💰 Fnd: ₹{sanitized_margin:,}", W))
    output_lines.append("-" * W)

    # 2. Active Working Orders Processing
    active_orders = []
    for o in orders_list:
        if not o:
            continue
        status = o.get("ordSt", o.get("status", "")) if isinstance(o, dict) else getattr(o, "ordSt", getattr(o, "status", ""))
        if str(status).lower() in ["working", "open", "validation pending"]:
            active_orders.append(o)

    output_lines.append(pad_row(f"⏳ Ord Working: {len(active_orders)}", W))
    for ord in active_orders:
        sym_raw = ord.get("trdSym", "UNK") if isinstance(ord, dict) else getattr(ord, "trdSym", "UNK")
        sym = str(sym_raw)[-7:]
        
        side_raw = ord.get("trnsTp", ord.get("side", "")) if isinstance(ord, dict) else getattr(ord, "trnsTp", getattr(ord, "side", ""))
        side = "B" if "B" in str(side_raw).upper() else "S"
        
        qty_raw = ord.get("fldQty", ord.get("qty", 0)) if isinstance(ord, dict) else getattr(ord, "fldQty", getattr(ord, "qty", 0))
        try:
            qty = abs(int(float(qty_raw)))
        except (ValueError, TypeError):
            qty = 0
        
        prc_raw = ord.get("price", ord.get("avgPrc", 0.0)) if isinstance(ord, dict) else getattr(ord, "price", getattr(ord, "avgPrc", 0.0))
        price = int(force_trailing_zero(prc_raw))
        
        line = f" 📝 {side}|{sym}|Q:{qty}|P:₹{price}"
        output_lines.append(pad_row(line, W))
    output_lines.append("-" * W)

    # 3. Active Positions & PnL Processing
    active_positions = []
    for p in positions_list:
        if not p:
            continue
        net_qty_raw = p.get("net_qty", p.get("netQty", 0)) if isinstance(p, dict) else getattr(p, "net_qty", getattr(p, "netQty", 0))
        try:
            net_qty = float(net_qty_raw)
        except (ValueError, TypeError):
            net_qty = 0.0
        
        if net_qty == 0:
            buy_qty = p.get("flBuyQty", p.get("buyQty", 0)) if isinstance(p, dict) else getattr(p, "flBuyQty", getattr(p, "buyQty", 0))
            sell_qty = p.get("flSellQty", p.get("sellQty", 0)) if isinstance(p, dict) else getattr(p, "flSellQty", getattr(p, "sellQty", 0))
            try:
                net_qty = float(buy_qty) - float(sell_qty)
            except (ValueError, TypeError):
                net_qty = 0.0
            
        if abs(net_qty) > 0:
            active_positions.append((p, net_qty))

    output_lines.append(pad_row(f"📊 Live Open: {len(active_positions)}", W))
    
    total_unrealized_pnl = 0.0
    for pos, qty in active_positions:
        sym_raw = pos.get("trdSym", "UNK") if isinstance(pos, dict) else getattr(pos, "trdSym", "UNK")
        sym = str(sym_raw)[-7:]
        
        buy_prc_raw = pos.get("buy_prc", pos.get("flBuyPrc", pos.get("buyAvgPrc", 0.0))) if isinstance(pos, dict) else getattr(pos, "buy_prc", getattr(pos, "flBuyPrc", getattr(pos, "buyAvgPrc", 0.0)))
        try:
            entry_prc = float(buy_prc_raw)
        except (ValueError, TypeError):
            entry_prc = 0.0
        
        ltp_raw = pos.get("sell_prc", pos.get("ltp", pos.get("lastPrice", 0.0))) if isinstance(pos, dict) else getattr(pos, "sell_prc", getattr(pos, "ltp", getattr(pos, "lastPrice", 0.0)))
        try:
            ltp = float(ltp_raw)
        except (ValueError, TypeError):
            ltp = 0.0
        
        raw_pnl = (ltp - entry_prc) * qty
        sanitized_pnl = int(force_trailing_zero(raw_pnl))
        total_unrealized_pnl += sanitized_pnl
        
        status_flag = "🟢" if sanitized_pnl >= 0 else "🔴"
        output_lines.append(pad_row(f" {status_flag} {sym} [Q:{int(qty)}]", W))
        pnl_str = f"₹{sanitized_pnl:,}"
        metrics = f"   E:{int(force_trailing_zero(entry_prc))}|L:{int(force_trailing_zero(ltp))}"
        
        space_needed = W - emoji_len(metrics) - emoji_len(pnl_str)
        if space_needed > 0:
            output_lines.append(f"{metrics}{' ' * space_needed}{pnl_str}")
        else:
            output_lines.append(pad_row(f"{metrics} P:{pnl_str}", W))
            
    output_lines.append("-" * W)
    
    # 4. Total Consolidated PnL Processing
    final_pnl = int(force_trailing_zero(total_unrealized_pnl))
    summary_label = "🏆 Net PnL:"
    pnl_val = f"₹{final_pnl:,}"
    sum_space = W - emoji_len(summary_label) - emoji_len(pnl_val)
    output_lines.append(f"{summary_label}{' ' * max(1, sum_space)}{pnl_val}")
    output_lines.append("=" * W)

    full_message_payload = "\n".join(output_lines)
    print(full_message_payload)

    telegram_formatted_msg = f"```text\n{full_message_payload}\n```"
    send_telegram_payload(telegram_formatted_msg)

if __name__ == "__main__":
    run_snapshot_report()


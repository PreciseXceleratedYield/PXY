#!/usr/bin/env python3
"""
PXY® Trading System - Ledger Snapshot Engine (exeldgrpxy.py)
Protected by international copyright laws. All rights reserved globally by PXY® and PreciseXceleratedYield Pvt Ltd™.

Purpose: Single-run snapshot formatted strictly to a 30-character maximum row width.
         Connects via runclntpxy.get_session() using real broker endpoints.
Design Rule: Guarantees that the last digit of calculated integer numbers ends in 0.
"""

import sys
import urllib.request
import urllib.parse
import pytz
from datetime import datetime, time
from runclntpxy import get_session

# 📬 Telegram API Endpoint Configuration (Placeholders)
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_PLACEHOLDER"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID_PLACEHOLDER"

IST = pytz.timezone("asia/kolkata")
W = 30  # Strict 30-character width tracking layout

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

    # Initialize connection via your native session manager
    client = get_session()
    if not client:
        print(pad_row("❌ API Connection Blank", W))
        return

    try:
        # Fetch live data arrays directly from broker endpoints
        margin_res = client.margin()
        pos_res = client.positions()
        ord_res = client.orders()
        
        # Unpack arrays securely using Kotak Neo V2 format models
        positions_list = pos_res.get("data", [])
        orders_list = ord_res.get("data", [])
        margin_data = margin_res.get("Margin", {})
        raw_margin = margin_data.get("availableMargin", 0.0)
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
    active_orders = [o for o in orders_list if str(o.get("status", "")).upper() == "WORKING"]
    output_lines.append(pad_row(f"⏳ Ord Working: {len(active_orders)}", W))
    for ord in active_orders:
        sym = str(ord.get("trdSym", "UNK"))[-7:]  # Keep strike context visible
        side = "B" if "BUY" in str(ord.get("side", "")).upper() else "S"
        qty = abs(int(float(ord.get("qty", 0))))
        price = int(force_trailing_zero(ord.get("price", 0.0)))
        
        line = f" 📝 {side}|{sym}|Q:{qty}|P:₹{price}"
        output_lines.append(pad_row(line, W))
    output_lines.append("-" * W)

    # 3. Active Positions & PnL Processing
    active_positions = [p for p in positions_list if int(float(p.get("net_qty", 0))) != 0]
    output_lines.append(pad_row(f"📊 Live Open: {len(active_positions)}", W))
    
    total_unrealized_pnl = 0.0
    for pos in active_positions:
        sym = str(pos.get("trdSym", "UNK"))[-7:]
        qty = int(float(pos.get("net_qty", 0)))
        entry_prc = float(pos.get("buy_prc", 0.0))
        ltp = float(pos.get("sell_prc", pos.get("ltp", 0.0)))
        
        raw_pnl = (ltp - entry_prc) * qty
        sanitized_pnl = int(force_trailing_zero(raw_pnl))
        total_unrealized_pnl += sanitized_pnl
        
        status_flag = "🟢" if sanitized_pnl >= 0 else "🔴"
        output_lines.append(pad_row(f" {status_flag} {sym} [Q:{qty}]", W))
        
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

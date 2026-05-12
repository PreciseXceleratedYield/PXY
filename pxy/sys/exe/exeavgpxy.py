# exeavgpxy.py
import os
import time
import pytz
from datetime import datetime, time as dt_time
from colorama import Fore, Style

# --- CONFIG ---
REBUY_ENABLED = True
MAX_LAYERS = 1 
COOL_DOWN_SECONDS = 300
SIDE_SWITCH = 2
LOSS_THRESHOLD = -10

def generate_pxy_tag():
    """Generates a pure timestamp tag: HHMMSS for 1:1 matching"""
    IST = pytz.timezone("Asia/Kolkata")
    return datetime.now(IST).strftime('%H%M%S')

def handle_side_averaging(client, df):
    """Main logic for layering buys with Tag-Based Tracking."""
    if df is None or df.empty:
        return

    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()

    # Time Guard: Only average during active market hours
    if not REBUY_ENABLED or not (dt_time(9,30) <= now <= dt_time(15,0)):
        return

    df['side'] = df['symbol'].astype(str).str[-2:].str.upper()

    def get_loss(row):
        entry = float(row.get("pxy_entry", 0))
        ltp = float(row.get("sell_prc", 0))
        return ((ltp - entry) / entry) * 100 if entry > 0 else 0

    ce_df = df[df['side'] == 'CE']
    pe_df = df[df['side'] == 'PE']

    ce_hit = not ce_df.empty and get_loss(ce_df.iloc[-1]) <= LOSS_THRESHOLD
    pe_hit = not pe_df.empty and get_loss(pe_df.iloc[-1]) <= LOSS_THRESHOLD

    # Decision Matrix
    if SIDE_SWITCH == 2:
        trigger_allowed = ce_hit and pe_hit
    else:
        trigger_allowed = ce_hit or pe_hit

    if not trigger_allowed:
        return

    for side, side_df in [('CE', ce_df), ('PE', pe_df)]:
        if side_df.empty:
            continue
        
        count = len(side_df)
        if get_loss(side_df.iloc[-1]) > LOSS_THRESHOLD:
            continue

        # Check Max Layers and Cooling
        if count >= MAX_LAYERS or is_cooling(side):
            continue

        last_order = side_df.iloc[-1]
        symbol = last_order['symbol']
        qty = abs(int(last_order['qty']))
        
        # GENERATE NEW TAG: Even for averaging, every order must have a unique ID
        new_tag = generate_pxy_tag()

        print(f"{Fore.YELLOW}📉 {side} Averaging Triggered. Loss: {get_loss(side_df.iloc[-1]):.2f}%")
        
        try:
            params = {
                "exchange_segment": "nse_fo",
                "product": "NRML",
                "price": "0",
                "order_type": "MKT",
                "quantity": str(qty),
                "trading_symbol": str(symbol),
                "transaction_type": "B",
                "validity": "DAY",
                "amo": "NO",
                "tag": new_tag  # <--- CRITICAL: Tagging the Rebuy
            }
            client.place_order(**params)
            set_cooling(side)
            print(f"{Fore.GREEN}{Style.BRIGHT}✅ SUCCESS: Layer {count+1} Added for {symbol} | TAG: {new_tag}")
        except Exception as e:
            print(f"{Fore.RED}❌ Rebuy Execution Failed: {e}")


